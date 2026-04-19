"""Dynamic weights per user mode.

Weights MUST sum to 1.0. Documented in the public spec.
"""
from typing import Dict
from schemas.user_mode import UserMode


JUNIOR_WEIGHTS: Dict[str, float] = {
    "skills": 0.40,
    "experience": 0.10,
    "education": 0.25,
    "keywords": 0.15,
    "semantic": 0.10,
}

PROFESSIONAL_WEIGHTS: Dict[str, float] = {
    "skills": 0.25,
    "experience": 0.40,
    "education": 0.05,
    "keywords": 0.10,
    "semantic": 0.20,
}


def get_weights(mode: UserMode) -> Dict[str, float]:
    if mode == UserMode.junior:
        return dict(JUNIOR_WEIGHTS)
    return dict(PROFESSIONAL_WEIGHTS)


# Sanity: enforce the invariant once at import time.
for _w in (JUNIOR_WEIGHTS, PROFESSIONAL_WEIGHTS):
    assert abs(sum(_w.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"
