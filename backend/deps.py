"""Shared dependencies (auth + db + settings) reused across routers.

Centralised here to avoid circular imports with server.py.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

_client = AsyncIOMotorClient(MONGO_URL)
db = _client[DB_NAME]


# --------- Tier limits ---------

FREE_DAILY_LIMIT = 3


class WorkExperience(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    headline: str = ""
    skills: List[str] = []
    experience: List[WorkExperience] = []
    cv_raw_text: str = ""
    mode: str = "professional"             # "junior" | "professional"
    tier: str = "FREE"                     # "FREE" | "PRO"
    daily_analyses_count: int = 0
    last_analysis_date: Optional[str] = None  # ISO date string (UTC)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _today_utc_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def enforce_daily_limit(user_id: str) -> dict:
    """Reset count if a new UTC day, then enforce FREE-tier limit. Returns the live user doc.

    Pure server-side time check (UTC) — los usuarios no pueden saltarse el límite cambiando
    su reloj local porque toda la lógica usa la hora del servidor.
    """
    today = _today_utc_iso()

    # 1) Reset if the stored date is not today (either older or null).
    await db.users.update_one(
        {"user_id": user_id, "last_analysis_date": {"$ne": today}},
        {"$set": {"daily_analyses_count": 0, "last_analysis_date": today}},
    )

    # 2) Re-read fresh user state.
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    tier = (user_doc.get("tier") or "FREE").upper()
    count = int(user_doc.get("daily_analyses_count") or 0)

    if tier == "FREE" and count >= FREE_DAILY_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=(
                "Has llegado al límite diario gratuito "
                f"({FREE_DAILY_LIMIT} análisis). Actualiza a Pro para análisis ilimitados."
            ),
        )
    return user_doc


async def increment_analysis_count(user_id: str) -> None:
    """Atomically bump the user's daily counter (after a successful AI call)."""
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"daily_analyses_count": 1},
            "$set": {"last_analysis_date": _today_utc_iso()},
        },
    )


async def get_current_user(request: Request) -> User:
    """Cookie first, then Authorization header. Raises 401 on any failure."""
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    user_doc.setdefault("mode", "professional")
    user_doc.setdefault("tier", "FREE")
    user_doc.setdefault("daily_analyses_count", 0)
    user_doc.setdefault("last_analysis_date", None)
    return User(**user_doc)
