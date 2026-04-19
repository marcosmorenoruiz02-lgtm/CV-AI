"""Thin LLM client wrapper around emergentintegrations.

Adds JSON-only helper with robust parsing (markdown-fence tolerant, repair attempt).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from emergentintegrations.llm.chat import LlmChat, UserMessage

from deps import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = ("openai", "gpt-5.2")


def _new_chat(system: str, session_id: str | None = None) -> LlmChat:
    sid = session_id or f"llm-{uuid.uuid4().hex[:10]}"
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sid, system_message=system)
    chat.with_model(*DEFAULT_MODEL)
    return chat


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


async def call_text(system: str, user_text: str, session_id: str | None = None) -> str:
    """Plain text completion."""
    chat = _new_chat(system, session_id)
    return await chat.send_message(UserMessage(text=user_text))


async def call_json(
    system: str,
    user_text: str,
    *,
    session_id: str | None = None,
    fallback: Any | None = None,
) -> Any:
    """Send a prompt that MUST return JSON. Returns parsed Python object.

    Robust to markdown fences and minor garbage. If parsing fails, returns
    `fallback` (or raises if fallback is None).
    """
    chat = _new_chat(system, session_id)
    raw = await chat.send_message(UserMessage(text=user_text))
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Recovery
    candidate = _extract_json_block(cleaned)
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)  # trailing commas
    try:
        return json.loads(candidate)
    except Exception as e:
        logger.warning("LLM JSON parse failed: %s | raw=%s", e, raw[:400])
        if fallback is not None:
            return fallback
        raise ValueError(f"LLM did not return valid JSON: {e}")
