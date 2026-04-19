"""Scoring schemas (analyze input/output, breakdown, recommendations)."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from .user_mode import UserMode


class ScoringBreakdown(BaseModel):
    """All sub-scores normalised to [0, 1]."""

    skills: float = 0.0
    experience: float = 0.0
    education: float = 0.0
    keywords: float = 0.0
    semantic: float = 0.0


class AnalyzeInput(BaseModel):
    mode: UserMode = UserMode.professional
    cv_text: str = Field(..., min_length=10)
    job_text: str = Field(..., min_length=10)
    persist: bool = True


class AnalyzeOutput(BaseModel):
    total_score: float
    breakdown: ScoringBreakdown
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    critical_gaps: List[str] = []
    minor_gaps: List[str] = []
    recommendations: List[str] = []
    semantic_explanation: Optional[str] = None
    mode: UserMode
    weights_used: dict
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    analysis_id: Optional[str] = None
