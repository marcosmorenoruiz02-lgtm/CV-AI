"""POST /api/quick-analyze — anonymous CV upload → ATS analysis in one shot.

Conversion gateway: lets the user see real value BEFORE creating an account.
"""
from __future__ import annotations

import io
import logging
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

from services.llm.client import call_json
from services.llm.prompts import CV_EXTRACTION_SYSTEM

router = APIRouter(prefix="/api", tags=["quick-analyze"])
logger = logging.getLogger(__name__)


QUICK_ANALYSIS_SYSTEM = """Eres un sistema ATS (Applicant Tracking System) y experto en CVs. Recibes el texto plano de un CV y devuelves EXCLUSIVAMENTE un JSON válido con este shape:

{
  "ats_score": int,           // 0-100, qué bien lo lee un ATS típico
  "format_score": int,        // 0-100, claridad/estructura/legibilidad
  "keyword_score": int,       // 0-100, densidad de keywords técnicas vs ruido
  "final_score": int,         // 0-100, ponderado (40% ats, 30% keyword, 30% format)
  "summary": str,             // 1-2 frases en tono cercano. Tú a tú. Sin tono corporativo.
  "problems": [str],          // 3-6 problemas concretos del CV (p.ej. "no tienes verbos de acción", "demasiada jerga genérica")
  "missing_keywords": [str],  // 5-15 keywords técnicas que probablemente deberían estar
  "top_improvements": [       // 3-5 mejoras priorizadas, orientadas a impacto
    {
      "title": str,
      "before": str,          // ejemplo del CV (corto)
      "after": str,           // reescritura concreta con métrica si es posible
      "why": str              // 1 frase, lenguaje claro
    }
  ],
  "detected_role": str,       // rol probable que está buscando (1 línea)
  "languages": [str]          // idiomas detectados
}

Reglas estrictas:
- Sé honesto con los scores: si el CV es flojo, ponlo bajo.
- NUNCA inventes datos del CV. Si no detectas una keyword, no te la inventes.
- Tono cercano y directo, sin pasivas ni "se recomienda".
- Cero emojis. Cero relleno. JSON puro, sin markdown."""


class QuickImprovement(BaseModel):
    title: str
    before: str = ""
    after: str = ""
    why: str = ""


class QuickAnalysisResult(BaseModel):
    final_score: int
    ats_score: int
    format_score: int
    keyword_score: int
    summary: str = ""
    problems: List[str] = []
    missing_keywords: List[str] = []
    top_improvements: List[QuickImprovement] = []
    detected_role: Optional[str] = None
    languages: List[str] = []
    cv_excerpt: str = ""  # first 500 chars (for "we read your CV" UX confidence)


@router.post("/quick-analyze", response_model=QuickAnalysisResult)
async def quick_analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El PDF supera los 8 MB")

    try:
        reader = PdfReader(io.BytesIO(content))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
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
        fallback={
            "ats_score": 0,
            "format_score": 0,
            "keyword_score": 0,
            "final_score": 0,
            "summary": "No pudimos analizar tu CV ahora mismo. Inténtalo en unos segundos.",
            "problems": [],
            "missing_keywords": [],
            "top_improvements": [],
            "detected_role": "",
            "languages": [],
        },
    )
    if not isinstance(parsed, dict):
        parsed = {}

    def _int(value, default=0) -> int:
        try:
            return max(0, min(100, int(round(float(value)))))
        except Exception:
            return default

    improvements_raw = parsed.get("top_improvements") or []
    improvements: List[QuickImprovement] = []
    for imp in improvements_raw:
        if not isinstance(imp, dict):
            continue
        improvements.append(
            QuickImprovement(
                title=str(imp.get("title") or "")[:120],
                before=str(imp.get("before") or "")[:300],
                after=str(imp.get("after") or "")[:300],
                why=str(imp.get("why") or "")[:240],
            )
        )

    return QuickAnalysisResult(
        final_score=_int(parsed.get("final_score") or parsed.get("ats_score")),
        ats_score=_int(parsed.get("ats_score")),
        format_score=_int(parsed.get("format_score")),
        keyword_score=_int(parsed.get("keyword_score")),
        summary=str(parsed.get("summary") or "")[:480],
        problems=[str(p) for p in (parsed.get("problems") or []) if p][:8],
        missing_keywords=[str(k) for k in (parsed.get("missing_keywords") or []) if k][:20],
        top_improvements=improvements[:6],
        detected_role=(parsed.get("detected_role") or None),
        languages=[str(l) for l in (parsed.get("languages") or []) if l][:6],
        cv_excerpt=raw_text[:500],
    )
