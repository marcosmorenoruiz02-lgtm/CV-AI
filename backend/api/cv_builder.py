"""POST /api/cv/build — generate structured CV (junior or professional mode).

Auto-runs the scoring engine if a job_text is provided to give immediate feedback.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from deps import User, db, get_current_user
from schemas.cv import CVBuildInput
from schemas.scoring import AnalyzeInput, AnalyzeOutput
from schemas.user_mode import UserMode
from services.cv_builder import build_cv, questionnaire_for_mode
from api.analysis import analyze as analyze_endpoint

router = APIRouter(prefix="/api/cv", tags=["cv-builder"])
logger = logging.getLogger(__name__)


class CVBuildRequest(BaseModel):
    mode: UserMode = UserMode.junior
    data: CVBuildInput
    job_text: Optional[str] = None  # if present, score the generated CV against this job
    persist: bool = True


class CVBuildResponse(BaseModel):
    cv_id: Optional[str] = None
    cv: dict
    scoring: Optional[AnalyzeOutput] = None


@router.get("/questionnaire")
async def questionnaire(
    mode: UserMode = Query(default=UserMode.junior),
    _: User = Depends(get_current_user),
):
    return {"mode": mode.value, "questions": questionnaire_for_mode(mode)}


@router.post("/build", response_model=CVBuildResponse)
async def build(payload: CVBuildRequest, user: User = Depends(get_current_user)):
    cv = await build_cv(payload.data, payload.mode)

    cv_id: Optional[str] = None
    if payload.persist:
        cv_id = f"cv_{uuid.uuid4().hex[:12]}"
        await db.generated_cvs.insert_one(
            {
                "id": cv_id,
                "user_id": user.user_id,
                "mode": payload.mode.value,
                "input": payload.data.model_dump(),
                "cv": cv,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    scoring_result: Optional[AnalyzeOutput] = None
    if payload.job_text and payload.job_text.strip():
        # Flatten the structured CV into a text blob for analysis.
        cv_text = _flatten_cv_to_text(cv, fallback_name=payload.data.name)
        try:
            scoring_result = await analyze_endpoint(
                AnalyzeInput(
                    mode=payload.mode,
                    cv_text=cv_text,
                    job_text=payload.job_text,
                    persist=False,
                ),
                user=user,
            )
        except Exception:
            logger.exception("Auto-scoring after CV build failed")

    return CVBuildResponse(cv_id=cv_id, cv=cv, scoring=scoring_result)


@router.get("/list")
async def list_cvs(user: User = Depends(get_current_user)):
    cursor = db.generated_cvs.find({"user_id": user.user_id}, {"_id": 0}).sort(
        "created_at", -1
    )
    return await cursor.to_list(100)


def _flatten_cv_to_text(cv: dict, fallback_name: str = "") -> str:
    parts = []
    if fallback_name:
        parts.append(fallback_name)
    if cv.get("headline"):
        parts.append(cv["headline"])
    if cv.get("summary"):
        parts.append(cv["summary"])
    if cv.get("skills"):
        parts.append("Skills: " + ", ".join(cv["skills"]))
    for exp in cv.get("experience", []):
        line = f"{exp.get('role','')} @ {exp.get('company','')} ({exp.get('period','')}): {exp.get('description','')}"
        parts.append(line)
        for b in exp.get("bullets", []):
            parts.append(f"- {b}")
    for proj in cv.get("projects", []):
        parts.append(
            f"Proyecto {proj.get('name','')} - {proj.get('description','')} "
            f"({', '.join(proj.get('technologies', []))})"
        )
        for b in proj.get("bullets", []):
            parts.append(f"- {b}")
    for edu in cv.get("education", []):
        parts.append(
            f"{edu.get('title','')} - {edu.get('institution','')} ({edu.get('period','')})"
        )
    return "\n".join(p for p in parts if p)
