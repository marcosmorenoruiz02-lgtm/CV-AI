"""CV-related Pydantic schemas (input for builder, structured CV output)."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------- CV Builder (Junior mode) ----------


class CVBuilderEducation(BaseModel):
    title: str = ""
    institution: str = ""
    period: str = ""
    description: str = ""


class CVBuilderProject(BaseModel):
    name: str = ""
    description: str = ""
    technologies: List[str] = []
    url: Optional[str] = None


class CVBuilderExperience(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class CVBuildInput(BaseModel):
    name: str = ""
    email: Optional[str] = None
    location: Optional[str] = None
    education: List[CVBuilderEducation] = []
    skills: List[str] = []
    interests: List[str] = []
    projects: List[CVBuilderProject] = []
    experience: List[CVBuilderExperience] = []
    target_role: Optional[str] = Field(
        default=None,
        description="Optional target role to bias the headline / summary.",
    )


# ---------- Structured CV (output of builder + cv extraction) ----------


class CVExperienceItem(BaseModel):
    role: str
    company: str = ""
    period: str = ""
    description: str = ""
    bullets: List[str] = []


class CVEducationItem(BaseModel):
    title: str
    institution: str = ""
    period: str = ""


class StructuredCV(BaseModel):
    headline: str = ""
    summary: str = ""
    skills: List[str] = []
    experience: List[CVExperienceItem] = []
    education: List[CVEducationItem] = []
    total_years_experience: float = 0
