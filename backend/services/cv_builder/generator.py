"""CV generator: turns raw user input into a structured CV via LLM."""
from __future__ import annotations

import json
import logging
from typing import Dict

from schemas.cv import CVBuildInput
from schemas.user_mode import UserMode
from services.llm.client import call_json
from services.llm.prompts import CV_BUILDER_JUNIOR_SYSTEM, CV_BUILDER_PROFESSIONAL_SYSTEM
from services.cv_builder.templates import empty_output

logger = logging.getLogger(__name__)


async def build_cv(payload: CVBuildInput, mode: UserMode) -> Dict:
    """Run the LLM with the right system prompt for the user mode."""
    system = (
        CV_BUILDER_JUNIOR_SYSTEM
        if mode == UserMode.junior
        else CV_BUILDER_PROFESSIONAL_SYSTEM
    )
    payload_json = payload.model_dump()
    user_text = (
        "DATOS DEL USUARIO (JSON):\n"
        + json.dumps(payload_json, ensure_ascii=False, indent=2)
        + "\n\nDevuelve SOLO el JSON del CV estructurado."
    )
    try:
        result = await call_json(system, user_text, fallback=empty_output())
    except Exception as e:
        logger.exception("CV builder LLM call failed: %s", e)
        result = empty_output()

    # Hard-guarantee shape
    out = empty_output()
    if isinstance(result, dict):
        for key in out.keys():
            if key in result and result[key] is not None:
                out[key] = result[key]
    # Defensive: ensure lists are lists
    for k in ("skills", "experience", "education", "projects"):
        if not isinstance(out.get(k), list):
            out[k] = []
    return out
