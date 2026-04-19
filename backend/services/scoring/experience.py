"""Experience scoring (years + relevance + role similarity)."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from services.scoring.normalization import normalize_skill


def years_score(cv_years: float, job_years: float) -> float:
    """min(cv / job, 1). If job_years == 0, treat as fully satisfied."""
    if not job_years or job_years <= 0:
        return 1.0
    if cv_years is None or cv_years < 0:
        return 0.0
    return max(0.0, min(cv_years / job_years, 1.0))


def role_similarity(cv_roles: Iterable[str], target_role: str) -> float:
    """Best string similarity between any past role and the target role."""
    if not target_role:
        return 0.0
    target = normalize_skill(target_role)
    best = 0.0
    for r in cv_roles or []:
        if not r:
            continue
        ratio = SequenceMatcher(None, normalize_skill(r), target).ratio()
        if ratio > best:
            best = ratio
    return float(best)


def experience_score(
    cv_years: float,
    job_years: float,
    relevance_score: float,
    role_sim: float,
) -> float:
    """0.5 * years + 0.3 * relevance + 0.2 * role_similarity."""
    y = years_score(cv_years, job_years)
    rel = max(0.0, min(float(relevance_score or 0.0), 1.0))
    rs = max(0.0, min(float(role_sim or 0.0), 1.0))
    return max(0.0, min(0.5 * y + 0.3 * rel + 0.2 * rs, 1.0))
