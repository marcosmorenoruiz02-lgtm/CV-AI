"""Scoring engine package."""
from .scorer import compute_total_score, keywords_score, count_keyword_hits, education_score
from .skill_matcher import match_skills
from .experience import experience_score, role_similarity, years_score
from .weights import get_weights, JUNIOR_WEIGHTS, PROFESSIONAL_WEIGHTS
from .normalization import normalize_skill, normalize_skills_list, normalize_keyword

__all__ = [
    "compute_total_score",
    "keywords_score",
    "count_keyword_hits",
    "education_score",
    "match_skills",
    "experience_score",
    "role_similarity",
    "years_score",
    "get_weights",
    "JUNIOR_WEIGHTS",
    "PROFESSIONAL_WEIGHTS",
    "normalize_skill",
    "normalize_skills_list",
    "normalize_keyword",
]
