"""Skill matching: weighted exact + similar-match scoring.

Pure deterministic logic, no LLM.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from schemas.job import JobSkill
from services.scoring.normalization import normalize_skill


SIMILAR_THRESHOLD = 0.82  # SequenceMatcher ratio
EXACT_SCORE = 1.0
SIMILAR_SCORE = 0.7


def _best_match(target: str, pool: List[str]) -> Tuple[str | None, float]:
    """Return (matched_skill_in_pool, match_score 0-1)."""
    if not target or not pool:
        return None, 0.0
    if target in pool:
        return target, EXACT_SCORE
    best, best_ratio = None, 0.0
    for candidate in pool:
        ratio = SequenceMatcher(None, target, candidate).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best_ratio >= SIMILAR_THRESHOLD:
        return best, SIMILAR_SCORE
    return None, 0.0


def match_skills(
    cv_skills: List[str],
    job_skills: List[JobSkill] | List[Dict] | List[str],
) -> Dict:
    """Compute weighted skill score plus matching/missing lists.

    Formula: score = sum(match_value * weight) / sum(weight)
    """
    cv_norm = [normalize_skill(s) for s in (cv_skills or []) if s]

    weighted: List[Tuple[str, float]] = []  # (normalised_name, weight)
    for s in job_skills or []:
        if isinstance(s, JobSkill):
            name, weight = s.name, float(s.weight or 1.0)
        elif isinstance(s, dict):
            name = s.get("name", "")
            weight = float(s.get("weight", 1.0) or 1.0)
        else:
            name, weight = str(s), 1.0
        n = normalize_skill(name)
        if n:
            weighted.append((n, max(weight, 0.0)))

    if not weighted:
        return {
            "score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
            "details": [],
        }

    total_weight = sum(w for _, w in weighted) or 1.0
    matching: List[str] = []
    missing: List[str] = []
    weighted_sum = 0.0
    details: List[Dict] = []

    for name, weight in weighted:
        matched_with, match_score = _best_match(name, cv_norm)
        weighted_sum += match_score * weight
        details.append(
            {
                "required": name,
                "weight": weight,
                "matched_with": matched_with,
                "match_score": match_score,
            }
        )
        if match_score >= SIMILAR_SCORE:
            matching.append(name)
        else:
            missing.append(name)

    score = weighted_sum / total_weight
    return {
        "score": max(0.0, min(1.0, score)),
        "matching_skills": matching,
        "missing_skills": missing,
        "details": details,
    }
