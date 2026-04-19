"""Top-level scorer that aggregates breakdown into total score 0-100."""
from __future__ import annotations

from typing import Dict, Iterable, List

from schemas.scoring import ScoringBreakdown
from schemas.user_mode import UserMode
from services.scoring.normalization import normalize_keyword
from services.scoring.weights import get_weights


def keywords_score(present: int, total: int) -> float:
    if total <= 0:
        return 1.0  # nothing required → perfect
    return max(0.0, min(present / total, 1.0))


def count_keyword_hits(cv_text: str, keywords: Iterable[str]) -> tuple[int, int, List[str], List[str]]:
    """Return (present, total, present_list, missing_list)."""
    text = (cv_text or "").lower()
    kws = [normalize_keyword(k) for k in keywords or [] if k]
    present_list: List[str] = []
    missing_list: List[str] = []
    for k in kws:
        if k and k in text:
            present_list.append(k)
        else:
            missing_list.append(k)
    return len(present_list), len(kws), present_list, missing_list


def education_score(label: str | float) -> float:
    """Accept '1', '0.5', '0' OR strings like 'cumple', 'parcial', 'no cumple'."""
    if isinstance(label, (int, float)):
        return max(0.0, min(float(label), 1.0))
    s = (label or "").strip().lower()
    if s in {"1", "cumple", "yes", "si", "true", "match"}:
        return 1.0
    if s in {"0.5", "parcial", "partial", "maybe"}:
        return 0.5
    return 0.0


def compute_total_score(breakdown: ScoringBreakdown, mode: UserMode) -> tuple[float, Dict[str, float]]:
    """Apply mode weights to the breakdown. Returns (score 0-100, weights_used)."""
    weights = get_weights(mode)
    total = (
        breakdown.skills * weights["skills"]
        + breakdown.experience * weights["experience"]
        + breakdown.education * weights["education"]
        + breakdown.keywords * weights["keywords"]
        + breakdown.semantic * weights["semantic"]
    )
    total = max(0.0, min(total, 1.0)) * 100.0
    return round(total, 2), weights
