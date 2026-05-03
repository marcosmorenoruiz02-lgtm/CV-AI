"""POST /api/analyze — dual-mode CV ↔ Job analysis with hybrid scoring."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from deps import User, db, enforce_daily_limit, get_current_user, increment_analysis_count
from schemas.cv import StructuredCV
from schemas.job import JobSkill, StructuredJob
from schemas.scoring import AnalyzeInput, AnalyzeOutput, ScoringBreakdown
from schemas.user_mode import UserMode
from services.llm.client import call_json
from services.llm.prompts import (
    CV_EXTRACTION_SYSTEM,
    GAP_ANALYSIS_SYSTEM_TEMPLATE,
    JOB_EXTRACTION_SYSTEM,
    SEMANTIC_MATCH_SYSTEM,
)
from services.scoring import (
    compute_total_score,
    count_keyword_hits,
    education_score,
    experience_score,
    keywords_score,
    match_skills,
    role_similarity,
)

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)


def _safe_cv(parsed: Dict) -> StructuredCV:
    if not isinstance(parsed, dict):
        return StructuredCV()
    safe = {
        "headline": parsed.get("headline") or "",
        "summary": parsed.get("summary") or "",
        "skills": [str(s) for s in (parsed.get("skills") or []) if s],
        "experience": [],
        "education": [],
        "total_years_experience": float(parsed.get("total_years_experience") or 0),
    }
    for exp in parsed.get("experience") or []:
        if not isinstance(exp, dict):
            continue
        safe["experience"].append(
            {
                "role": exp.get("role") or "",
                "company": exp.get("company") or "",
                "period": exp.get("period") or "",
                "description": exp.get("description") or "",
                "bullets": [str(b) for b in (exp.get("bullets") or []) if b],
            }
        )
    for edu in parsed.get("education") or []:
        if not isinstance(edu, dict):
            continue
        safe["education"].append(
            {
                "title": edu.get("title") or "",
                "institution": edu.get("institution") or "",
                "period": edu.get("period") or "",
            }
        )
    return StructuredCV(**safe)


def _safe_job(parsed: Dict) -> StructuredJob:
    if not isinstance(parsed, dict):
        return StructuredJob()
    skills_raw = parsed.get("skills") or []
    skills: List[JobSkill] = []
    for s in skills_raw:
        if isinstance(s, dict) and s.get("name"):
            try:
                skills.append(JobSkill(name=str(s["name"]), weight=float(s.get("weight") or 1.0)))
            except Exception:
                continue
        elif isinstance(s, str):
            skills.append(JobSkill(name=s, weight=1.0))
    return StructuredJob(
        title=parsed.get("title") or "",
        company=parsed.get("company") or "",
        skills=skills,
        required_years=float(parsed.get("required_years") or 0),
        education_required=parsed.get("education_required") or "",
        keywords=[str(k) for k in (parsed.get("keywords") or []) if k],
        role_summary=parsed.get("role_summary") or "",
    )


async def _extract_cv(cv_text: str, tier: str | None = None) -> StructuredCV:
    parsed = await call_json(
        CV_EXTRACTION_SYSTEM, f"TEXTO DEL CV:\n\n{cv_text[:18000]}", fallback={}, tier=tier,
    )
    return _safe_cv(parsed)


async def _extract_job(job_text: str, tier: str | None = None) -> StructuredJob:
    parsed = await call_json(
        JOB_EXTRACTION_SYSTEM, f"TEXTO DE LA OFERTA:\n\n{job_text[:18000]}", fallback={}, tier=tier,
    )
    return _safe_job(parsed)


async def _semantic_match(cv: StructuredCV, job: StructuredJob, tier: str | None = None) -> Dict:
    payload = {
        "cv": cv.model_dump(),
        "job": job.model_dump(),
    }
    parsed = await call_json(
        SEMANTIC_MATCH_SYSTEM,
        f"DATOS:\n{json.dumps(payload, ensure_ascii=False)}",
        tier=tier,
        fallback={
            "semantic_score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
            "relevance_score": 0.0,
            "explanation": "",
        },
    )
    if not isinstance(parsed, dict):
        parsed = {}
    return {
        "semantic_score": max(0.0, min(float(parsed.get("semantic_score") or 0.0), 1.0)),
        "matching_skills": [str(x) for x in parsed.get("matching_skills") or [] if x],
        "missing_skills": [str(x) for x in parsed.get("missing_skills") or [] if x],
        "relevance_score": max(0.0, min(float(parsed.get("relevance_score") or 0.0), 1.0)),
        "explanation": parsed.get("explanation") or "",
    }


async def _gap_analysis(
    mode: UserMode,
    cv: StructuredCV,
    job: StructuredJob,
    missing_skills: List[str],
    total_score: float,
    tier: str | None = None,
) -> Dict:
    system = GAP_ANALYSIS_SYSTEM_TEMPLATE.format(mode=mode.value)
    payload = {
        "cv": cv.model_dump(),
        "job": job.model_dump(),
        "missing_skills": missing_skills,
        "total_score": total_score,
    }
    parsed = await call_json(
        system,
        f"DATOS:\n{json.dumps(payload, ensure_ascii=False)}",
        tier=tier,
        fallback={"critical_gaps": [], "minor_gaps": [], "recommendations": []},
    )
    if not isinstance(parsed, dict):
        parsed = {}
    return {
        "critical_gaps": [str(x) for x in parsed.get("critical_gaps") or [] if x][:8],
        "minor_gaps": [str(x) for x in parsed.get("minor_gaps") or [] if x][:8],
        "recommendations": [str(x) for x in parsed.get("recommendations") or [] if x][:10],
    }


@router.post("/analyze", response_model=AnalyzeOutput)
async def analyze(payload: AnalyzeInput, user: User = Depends(get_current_user)):
    mode = payload.mode

    # Daily quota enforcement (FREE tier capped, PRO unlimited).
    user_doc = await enforce_daily_limit(user.user_id)
    tier = (user_doc.get("tier") or "FREE").upper()

    # 1. Structured extraction (parallelisable, but keep simple/sequential).
    try:
        cv = await _extract_cv(payload.cv_text, tier=tier)
        job = await _extract_job(payload.job_text, tier=tier)
    except Exception as e:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=502, detail=f"Fallo al extraer estructura: {e}")

    # 2. Semantic match (LLM)
    try:
        sem = await _semantic_match(cv, job, tier=tier)
    except Exception:
        logger.exception("Semantic match failed")
        sem = {
            "semantic_score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
            "relevance_score": 0.0,
            "explanation": "",
        }

    # 3. Deterministic scoring
    skills_res = match_skills(cv.skills, job.skills)
    cv_roles = [e.role for e in cv.experience]
    rs = role_similarity(cv_roles, job.title)
    exp_score = experience_score(
        cv_years=cv.total_years_experience,
        job_years=job.required_years,
        relevance_score=sem["relevance_score"],
        role_sim=rs,
    )
    edu_score = education_score(_education_label(cv, job))
    present, total, present_kw, missing_kw = count_keyword_hits(
        payload.cv_text, job.keywords
    )
    kw_score = keywords_score(present, total)
    breakdown = ScoringBreakdown(
        skills=round(skills_res["score"], 4),
        experience=round(exp_score, 4),
        education=round(edu_score, 4),
        keywords=round(kw_score, 4),
        semantic=round(sem["semantic_score"], 4),
    )
    total_score, weights = compute_total_score(breakdown, mode)

    # Merge missing skills (deterministic + semantic), de-dup preserving order
    deterministic_missing = skills_res["missing_skills"]
    semantic_missing = sem["missing_skills"]
    merged_missing: List[str] = []
    seen = set()
    for s in deterministic_missing + semantic_missing + missing_kw:
        sl = s.lower()
        if sl and sl not in seen:
            seen.add(sl)
            merged_missing.append(s)

    deterministic_matching = skills_res["matching_skills"]
    semantic_matching = sem["matching_skills"]
    merged_matching: List[str] = []
    seen2 = set()
    for s in deterministic_matching + semantic_matching:
        sl = s.lower()
        if sl and sl not in seen2:
            seen2.add(sl)
            merged_matching.append(s)

    # 4. Gap analysis (LLM)
    try:
        gaps = await _gap_analysis(mode, cv, job, merged_missing, total_score, tier=tier)
    except Exception:
        logger.exception("Gap analysis failed")
        gaps = {"critical_gaps": [], "minor_gaps": [], "recommendations": []}

    # 5. Persist
    analysis_id: str | None = None
    if payload.persist:
        analysis_id = f"a_{uuid.uuid4().hex[:12]}"
        await db.analyses.insert_one(
            {
                "id": analysis_id,
                "user_id": user.user_id,
                "mode": mode.value,
                "job_title": job.title or "Análisis",
                "job_company": job.company or "",
                "job_description": payload.job_text,
                "cv_text": payload.cv_text,
                "structured_cv": cv.model_dump(),
                "structured_job": job.model_dump(),
                "breakdown": breakdown.model_dump(),
                "total_score": total_score,
                "matching_skills": merged_matching,
                "missing_skills": merged_missing,
                "critical_gaps": gaps["critical_gaps"],
                "minor_gaps": gaps["minor_gaps"],
                "recommendations": gaps["recommendations"],
                "semantic_explanation": sem["explanation"],
                "weights_used": weights,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Count this successful call against the user's daily quota (FREE tier).
    await increment_analysis_count(user.user_id)

    return AnalyzeOutput(
        total_score=total_score,
        breakdown=breakdown,
        matching_skills=merged_matching,
        missing_skills=merged_missing,
        critical_gaps=gaps["critical_gaps"],
        minor_gaps=gaps["minor_gaps"],
        recommendations=gaps["recommendations"],
        semantic_explanation=sem["explanation"],
        mode=mode,
        weights_used=weights,
        job_title=job.title or None,
        job_company=job.company or None,
        analysis_id=analysis_id,
    )


def _education_label(cv: StructuredCV, job: StructuredJob) -> str:
    """Naive deterministic education match: 1 if the job mentions a level the CV has."""
    job_req = (job.education_required or "").lower().strip()
    if not job_req:
        return "1"
    cv_titles = " | ".join((e.title or "").lower() for e in cv.education)
    if not cv_titles:
        return "0"
    # Buckets
    high = ("phd", "doctor", "doctorado")
    mid = ("master", "máster", "mba", "postgrado", "posgrado")
    low = ("grado", "ingenier", "licenciat", "bachelor", "diploma", "fp", "técnico", "tecnologo", "tecnólogo")
    def bucket(text: str) -> int:
        if any(k in text for k in high):
            return 3
        if any(k in text for k in mid):
            return 2
        if any(k in text for k in low):
            return 1
        return 0
    req_b = bucket(job_req)
    cv_b = bucket(cv_titles)
    if cv_b >= req_b and req_b > 0:
        return "1"
    if cv_b > 0 and req_b > 0:
        return "0.5"
    return "0"
