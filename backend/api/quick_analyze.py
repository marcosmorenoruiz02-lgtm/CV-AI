"""POST /api/quick-analyze — anonymous CV upload → ATS analysis + optional job-match.

Conversion gateway: real value WITHOUT requiring login.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

from services.llm.client import call_json
from services.llm.prompts import (
    CV_OPTIMIZER_SYSTEM,
    JOB_EXTRACTION_SYSTEM,
    JOB_NORMALIZATION_SYSTEM,
    SIMPLE_LANGUAGE_RULES,
)
from services.scraper import ScrapeError, fetch_and_clean

router = APIRouter(prefix="/api", tags=["quick-analyze"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB raw upload cap (FastAPI / Starlette)
MAX_PAGES = 10                        # ignore anything beyond the first N pages
CHUNK_SIZE = 1024 * 1024              # 1 MB chunks when streaming to disk


# ----------------- Prompts specific to this endpoint -----------------

QUICK_ANALYSIS_SYSTEM = (
    """Eres un sistema ATS (Applicant Tracking System) y experto en CVs. Recibes el texto plano de un CV y devuelves EXCLUSIVAMENTE un JSON válido con este shape:

{
  "ats_score": int,                 // 0-100, qué bien lo lee un ATS típico
  "format_score": int,              // 0-100, claridad/estructura/legibilidad
  "keyword_score": int,             // 0-100, densidad de keywords técnicas vs ruido
  "final_score": int,               // 0-100, ponderado (40% ats, 30% keyword, 30% format)
  "explicacion": str,               // 1-2 frases EN LENGUAJE MUY SIMPLE explicando el score
  "errores_clave": [str],           // 3-6 errores del CV explicados como se lo dirías a alguien no técnico
  "como_mejorarlo": [str],          // 3-7 acciones concretas y fáciles de hacer
  "ejemplo_mejora": [                // 3-5 reescrituras concretas
    {"title": str, "before": str, "after": str, "why": str}
  ],
  "missing_keywords": [str],        // 5-15 keywords que deberían estar
  "detected_role": str,             // rol probable (1 línea)
  "languages": [str],               // idiomas detectados
  "personal_brand": str,            // 1 frase que define a la persona
  "strengths": [str],               // 3-5 fortalezas claras del CV
  "weak_signals": [str]             // 2-5 señales débiles a mejorar
}

Reglas duras:
- Sé HONESTO con los scores. Si el CV es flojo, ponlo bajo.
- NUNCA inventes datos del CV. Si no ves una keyword, no te la inventes.
- Usa tono cercano, como si hablaras con un amigo que busca trabajo y no es técnico.
- Cero emojis. JSON puro, sin markdown.
"""
    + "\n"
    + SIMPLE_LANGUAGE_RULES
)


SIMPLE_MATCH_SYSTEM = (
    """Eres un reclutador que explica las cosas claras y con empatía. Recibes un CV estructurado y una OFERTA ya normalizada (core_skills, must_have, nice_to_have, seniority). Devuelves EXCLUSIVAMENTE JSON válido:

{
  "match_score": int,           // 0-100
  "explicacion": str,           // 1-2 frases en lenguaje SIMPLE: ¿encajas o no?
  "matching_skills": [str],     // lo que SÍ cumples
  "missing_skills": [str],      // lo que NO cumples
  "critical_gaps": [str],       // 1-4 cosas que pueden tumbarte, explicadas simple
  "recommendations": [str]      // 3-6 pasos concretos para aumentar probabilidades
}

Reglas:
- Honesto con el score. Un 90 = match casi perfecto.
- NO inventes skills.
"""
    + "\n"
    + SIMPLE_LANGUAGE_RULES
)


# ----------------- Response models -----------------


class QuickImprovement(BaseModel):
    title: str
    before: str = ""
    after: str = ""
    why: str = ""


class NormalizedJob(BaseModel):
    job_title: str = ""
    company: str = ""
    location: str = ""
    seniority_level: str = ""
    core_skills: List[str] = []
    secondary_skills: List[str] = []
    must_have: List[str] = []
    nice_to_have: List[str] = []
    keywords_priority: List[str] = []
    requirements: List[str] = []
    responsibilities: List[str] = []
    source_url: Optional[str] = None


class JobMatch(BaseModel):
    match_score: int = 0
    explicacion: str = ""
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    critical_gaps: List[str] = []
    recommendations: List[str] = []


class QuickAnalysisResult(BaseModel):
    final_score: int
    ats_score: int
    format_score: int
    keyword_score: int
    explicacion: str = ""
    errores_clave: List[str] = []
    como_mejorarlo: List[str] = []
    ejemplo_mejora: List[QuickImprovement] = []
    missing_keywords: List[str] = []
    detected_role: Optional[str] = None
    languages: List[str] = []
    personal_brand: Optional[str] = None
    strengths: List[str] = []
    weak_signals: List[str] = []
    cv_excerpt: str = ""
    pages_read: int = 0
    # Optional job-match section (populated only when job_url is provided)
    job: Optional[NormalizedJob] = None
    job_match: Optional[JobMatch] = None


# ----------------- Helpers -----------------


async def _stream_to_tempfile(file: UploadFile) -> tuple[str, int]:
    """Write upload to /tmp in 1MB chunks. Returns (path, bytes_written)."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    total = 0
    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(status_code=413, detail="El PDF supera los 50 MB")
            tmp.write(chunk)
    finally:
        tmp.close()
    return tmp.name, total


def _extract_pdf_text(path: str) -> tuple[str, int]:
    """Read up to MAX_PAGES and return (text, pages_read). Clean headers/footers."""
    reader = PdfReader(path)
    page_count = min(len(reader.pages), MAX_PAGES)
    raw_pages: List[str] = []
    for i in range(page_count):
        try:
            raw_pages.append(reader.pages[i].extract_text() or "")
        except Exception:
            raw_pages.append("")
    text = _clean_repeated_lines("\n".join(raw_pages))
    return text, page_count


def _clean_repeated_lines(text: str) -> str:
    """Remove lines that repeat across pages (headers / footers / page numbers)."""
    # Drop empty & hyperline-looking text, collapse 3+ blank lines
    text = re.sub(r"\u0000", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    # Count line occurrences; drop ones that repeat > 2 times and are short (likely headers/footers)
    counts: Dict[str, int] = {}
    for ln in lines:
        if not ln:
            continue
        counts[ln] = counts.get(ln, 0) + 1
    cleaned: List[str] = []
    for ln in lines:
        if not ln:
            cleaned.append("")
            continue
        if len(ln) < 60 and counts.get(ln, 0) >= 3:
            continue  # repeated header/footer
        # Page number lines like "Page 3 of 10" or just "3 / 10"
        if re.fullmatch(r"(page\s*)?\d+\s*(/|of|de)\s*\d+", ln, flags=re.IGNORECASE):
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def _int(value: Any, default: int = 0) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return default


def _str_list(raw: Any, limit: int) -> List[str]:
    return [str(x) for x in (raw or []) if x][:limit]


def _parse_improvements(raw: Any) -> List[QuickImprovement]:
    out: List[QuickImprovement] = []
    for imp in raw or []:
        if not isinstance(imp, dict):
            continue
        out.append(
            QuickImprovement(
                title=str(imp.get("title") or "")[:120],
                before=str(imp.get("before") or "")[:300],
                after=str(imp.get("after") or "")[:300],
                why=str(imp.get("why") or "")[:240],
            )
        )
    return out


async def _analyze_job_url(url: str) -> tuple[NormalizedJob, dict]:
    """Scrape → extract → normalise. Returns (normalised, structured_raw_for_match)."""
    try:
        text, final_url = await fetch_and_clean(url)
    except ScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await _structure_job_text(text, source_url=final_url)


async def _structure_job_text(text: str, source_url: Optional[str] = None) -> tuple[NormalizedJob, dict]:
    """Common path: raw job text → extracted JSON → normalised JSON.

    Raises 422 with a human-friendly message if the LLM thinks the text is not
    a real job posting.
    """
    extracted = await call_json(
        JOB_EXTRACTION_SYSTEM,
        f"TEXTO DE LA OFERTA{f' (URL: {source_url})' if source_url else ''}:\n\n{text[:18000]}",
        fallback={},
    )
    if not isinstance(extracted, dict):
        extracted = {}

    normalised = await call_json(
        JOB_NORMALIZATION_SYSTEM,
        f"OFERTA EXTRAÍDA:\n{json.dumps(extracted, ensure_ascii=False)}",
        fallback={},
    )
    if not isinstance(normalised, dict):
        normalised = {}

    is_valid = bool(normalised.get("is_valid_job", True))
    has_signal = bool(
        extracted.get("title")
        or extracted.get("requirements")
        or extracted.get("responsibilities")
        or normalised.get("core_skills")
    )
    if not is_valid or not has_signal:
        raise HTTPException(
            status_code=422,
            detail=(
                "No pude encontrar una oferta de trabajo en este enlace. "
                "¿Pruebas a copiar el texto de la oferta directamente?"
            ),
        )

    return (
        NormalizedJob(
            job_title=str(extracted.get("title") or "")[:120],
            company=str(extracted.get("company") or "")[:120],
            location=str(extracted.get("location") or "")[:120],
            seniority_level=str(normalised.get("seniority_level") or ""),
            core_skills=_str_list(normalised.get("core_skills"), 10),
            secondary_skills=_str_list(normalised.get("secondary_skills"), 15),
            must_have=_str_list(normalised.get("must_have"), 10),
            nice_to_have=_str_list(normalised.get("nice_to_have"), 10),
            keywords_priority=_str_list(normalised.get("keywords_priority"), 12),
            requirements=_str_list(extracted.get("requirements"), 10),
            responsibilities=_str_list(extracted.get("responsibilities"), 10),
            source_url=source_url,
        ),
        {**extracted, "normalised": normalised},
    )


async def _match_cv_to_job(cv_raw: dict, job_struct: dict) -> JobMatch:
    parsed = await call_json(
        SIMPLE_MATCH_SYSTEM,
        f"CV:\n{json.dumps(cv_raw, ensure_ascii=False)}\n\nOFERTA:\n{json.dumps(job_struct, ensure_ascii=False)}",
        fallback={
            "match_score": 0,
            "explicacion": "",
            "matching_skills": [],
            "missing_skills": [],
            "critical_gaps": [],
            "recommendations": [],
        },
    )
    if not isinstance(parsed, dict):
        parsed = {}
    return JobMatch(
        match_score=_int(parsed.get("match_score")),
        explicacion=str(parsed.get("explicacion") or "")[:400],
        matching_skills=_str_list(parsed.get("matching_skills"), 15),
        missing_skills=_str_list(parsed.get("missing_skills"), 15),
        critical_gaps=_str_list(parsed.get("critical_gaps"), 6),
        recommendations=_str_list(parsed.get("recommendations"), 8),
    )


# ----------------- Endpoints -----------------


@router.post("/quick-analyze", response_model=QuickAnalysisResult)
async def quick_analyze(
    file: UploadFile = File(...),
    job_url: Optional[str] = Form(default=None),
    job_text: Optional[str] = Form(default=None),
):
    """Analyse a CV. Optionally match it against a job posting (URL or pasted text)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    tmp_path, _bytes = await _stream_to_tempfile(file)
    try:
        try:
            raw_text, pages_read = _extract_pdf_text(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

        if not raw_text.strip() or len(raw_text.strip()) < 80:
            raise HTTPException(
                status_code=422,
                detail="No detectamos texto en el PDF. ¿Lo exportaste como imagen?",
            )

        parsed = await call_json(
            QUICK_ANALYSIS_SYSTEM,
            f"TEXTO DEL CV:\n\n{raw_text[:15000]}",
            fallback={},
        )
        if not isinstance(parsed, dict):
            parsed = {}

        result = QuickAnalysisResult(
            final_score=_int(parsed.get("final_score") or parsed.get("ats_score")),
            ats_score=_int(parsed.get("ats_score")),
            format_score=_int(parsed.get("format_score")),
            keyword_score=_int(parsed.get("keyword_score")),
            explicacion=str(parsed.get("explicacion") or parsed.get("summary") or "")[:480],
            errores_clave=_str_list(parsed.get("errores_clave") or parsed.get("problems"), 8),
            como_mejorarlo=_str_list(parsed.get("como_mejorarlo"), 8),
            ejemplo_mejora=_parse_improvements(
                parsed.get("ejemplo_mejora") or parsed.get("top_improvements")
            )[:6],
            missing_keywords=_str_list(parsed.get("missing_keywords"), 20),
            detected_role=(parsed.get("detected_role") or None),
            languages=_str_list(parsed.get("languages"), 6),
            personal_brand=(parsed.get("personal_brand") or None),
            strengths=_str_list(parsed.get("strengths"), 6),
            weak_signals=_str_list(parsed.get("weak_signals"), 6),
            cv_excerpt=raw_text[:500],
            pages_read=pages_read,
        )

        # Optional job match: URL or pasted text
        if (job_url and job_url.strip()) or (job_text and job_text.strip()):
            try:
                if job_url and job_url.strip():
                    normalised, job_struct = await _analyze_job_url(job_url.strip())
                else:
                    normalised, job_struct = await _structure_job_text(job_text.strip())
                match = await _match_cv_to_job(parsed, job_struct)
                result.job = normalised
                result.job_match = match
            except HTTPException:
                raise
            except Exception:
                logger.exception("Job match step failed")
                # Non-fatal: return the CV analysis without match.

        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ----------------- /analyze-job-url (URL only) -----------------


class JobUrlRequest(BaseModel):
    url: str


@router.post("/analyze-job-url", response_model=NormalizedJob)
async def analyze_job_url(payload: JobUrlRequest):
    """Public endpoint: scrape + structure + normalise a job posting URL."""
    normalised, _raw = await _analyze_job_url(payload.url)
    return normalised


# ----------------- /optimize-cv (STAR rewrite) -----------------


class OptimizeRequest(BaseModel):
    cv_text: str
    target_role: Optional[str] = None


class OptimizedExperienceItem(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    bullets: List[str] = []


class OptimizeResult(BaseModel):
    improved_summary: str = ""
    optimized_experience: List[OptimizedExperienceItem] = []
    bullet_points: List[str] = []
    optimized_cv_text: str = ""


@router.post("/optimize-cv", response_model=OptimizeResult)
async def optimize_cv(payload: OptimizeRequest):
    """Reescribe el CV con método STAR. Anonymous: ideal para mostrar valor antes de pedir login."""
    txt = (payload.cv_text or "").strip()
    if len(txt) < 80:
        raise HTTPException(status_code=400, detail="Necesitamos el texto completo de tu CV.")

    instr = (
        f"TARGET_ROLE (sesga el tono hacia este rol si está): {payload.target_role}\n\n"
        if payload.target_role
        else ""
    )
    parsed = await call_json(
        CV_OPTIMIZER_SYSTEM,
        f"{instr}TEXTO DEL CV:\n\n{txt[:15000]}",
        fallback={
            "improved_summary": "",
            "optimized_experience": [],
            "bullet_points": [],
            "optimized_cv_text": "",
        },
    )
    if not isinstance(parsed, dict):
        parsed = {}

    exp_raw = parsed.get("optimized_experience") or []
    experience: List[OptimizedExperienceItem] = []
    for it in exp_raw:
        if not isinstance(it, dict):
            continue
        experience.append(
            OptimizedExperienceItem(
                role=str(it.get("role") or "")[:120],
                company=str(it.get("company") or "")[:120],
                period=str(it.get("period") or "")[:60],
                bullets=_str_list(it.get("bullets"), 8),
            )
        )

    return OptimizeResult(
        improved_summary=str(parsed.get("improved_summary") or "")[:1200],
        optimized_experience=experience[:10],
        bullet_points=_str_list(parsed.get("bullet_points"), 12),
        optimized_cv_text=str(parsed.get("optimized_cv_text") or "")[:8000],
    )
