"""Thin LLM client wrapper around emergentintegrations.

Adds JSON-only helper with robust parsing (markdown-fence tolerant, repair attempt).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

from emergentintegrations.llm.chat import LlmChat, UserMessage

from deps import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = ("openai", "gpt-5.2")
FALLBACK_MODEL = ("openai", "gpt-5.1")
LLM_CALL_TIMEOUT_S = 45.0  # hard cap per model attempt


# Per-tier configuration. The PRO tier uses the latest powerful model with more tokens.
# The FREE tier uses a lighter / cheaper model with tighter budgets.
TIER_MODELS = {
    "FREE": ("openai", "gpt-5.1"),
    "PRO": ("openai", "gpt-5.2"),
}


def _new_chat(system: str, session_id: str | None = None, model: tuple[str, str] | None = None) -> LlmChat:
    sid = session_id or f"llm-{uuid.uuid4().hex[:10]}"
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message=system)
    chat.with_model(*(model or DEFAULT_MODEL))
    return chat


def _models_for_tier(tier: str | None) -> list[tuple[str, str]]:
    """Return the ordered list of model attempts for a given tier."""
    t = (tier or "FREE").upper()
    if t == "PRO":
        # Pro: best model first, fallback to lighter.
        return [DEFAULT_MODEL, FALLBACK_MODEL]
    # Free: lighter model first to save budget; fallback to the bigger one if lighter fails.
    return [TIER_MODELS["FREE"], DEFAULT_MODEL]


def _strip_fences(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return s
    if s.startswith("```"):
        # remove opening fence
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s[3:]
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s


def _extract_json_block(text: str) -> str:
    """Best-effort recovery: find the first {...} or [...] block."""
    if not text:
        return text
    # Try object first, then array
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
    return text


async def call_text(
    system: str,
    user_text: str,
    session_id: str | None = None,
    *,
    tier: str | None = None,
) -> str:
    """Plain text completion with hard timeout + tier-aware model selection."""
    for model in _models_for_tier(tier):
        try:
            chat = _new_chat(system, session_id, model=model)
            return await asyncio.wait_for(
                chat.send_message(UserMessage(text=user_text)),
                timeout=LLM_CALL_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning("LLM call (%s) timed out after %ss", model, LLM_CALL_TIMEOUT_S)
        except Exception as e:
            logger.warning("LLM call (%s) failed: %s", model, e)
    raise RuntimeError("Both primary and fallback LLM models failed")


async def call_json(
    system: str,
    user_text: str,
    *,
    session_id: str | None = None,
    fallback: Any | None = None,
    tier: str | None = None,
) -> Any:
    """Send a prompt that MUST return JSON. Tier-aware model selection."""
    raw = None
    for model in _models_for_tier(tier):
        try:
            chat = _new_chat(system, session_id, model=model)
            raw = await asyncio.wait_for(
                chat.send_message(UserMessage(text=user_text)),
                timeout=LLM_CALL_TIMEOUT_S,
            )
            break
        except asyncio.TimeoutError:
            logger.warning("LLM call (%s) timed out after %ss", model, LLM_CALL_TIMEOUT_S)
            raw = None
        except Exception as e:
            logger.warning("LLM call (%s) failed: %s", model, e)
            raw = None
    if raw is None:
        if fallback is not None:
            return fallback
        raise RuntimeError("Both primary and fallback LLM models failed")

    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    candidate = _extract_json_block(cleaned)
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)  # trailing commas
    try:
        return json.loads(candidate)
    except Exception as e:
        logger.warning("LLM JSON parse failed: %s | raw=%s", e, raw[:400])
        if fallback is not None:
            return fallback
        raise ValueError(f"LLM did not return valid JSON: {e}")
