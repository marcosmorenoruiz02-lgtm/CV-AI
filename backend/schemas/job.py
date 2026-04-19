"""Job-related Pydantic schemas (structured job + import input)."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class JobSkill(BaseModel):
    name: str
    weight: float = 1.0


class StructuredJob(BaseModel):
    title: str = ""
    company: str = ""
    skills: List[JobSkill] = Field(default_factory=list)
    required_years: float = 0
    education_required: str = ""
    keywords: List[str] = []
    role_summary: str = ""


class JobImportInput(BaseModel):
    url: str
