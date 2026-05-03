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

# Free users get 4 analyses per calendar month (UTC). Pro users are unlimited
# while their paid subscription is active (pro_expires_at in the future).
FREE_MONTHLY_LIMIT = 4


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
    mode: str = "professional"                 # "junior" | "professional"
    tier: str = "FREE"                         # "FREE" | "PRO"
    monthly_analyses_count: int = 0
    last_analysis_month: Optional[str] = None  # "YYYY-MM" in UTC
    pro_expires_at: Optional[datetime] = None  # When the Pro access lapses → back to FREE
    stripe_customer_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _current_month_utc() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _is_pro_active(user_doc: dict) -> bool:
    if (user_doc.get("tier") or "FREE").upper() != "PRO":
        return False
    exp = user_doc.get("pro_expires_at")
    if exp is None:
        return False  # PRO flag without expiry → treat as expired
    if isinstance(exp, str):
        try:
            exp = datetime.fromisoformat(exp)
        except ValueError:
            return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > datetime.now(timezone.utc)


async def enforce_monthly_limit(user_id: str) -> dict:
    """Reset monthly counter if the month changed, downgrade expired PRO users,
    then enforce FREE-tier limit. Server-side UTC check (user clocks can't bypass)."""
    this_month = _current_month_utc()

    # 1) Reset counter if a new UTC month started.
    await db.users.update_one(
        {"user_id": user_id, "last_analysis_month": {"$ne": this_month}},
        {"$set": {"monthly_analyses_count": 0, "last_analysis_month": this_month}},
    )

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    # 2) Downgrade expired PRO users back to FREE.
    if (user_doc.get("tier") or "FREE").upper() == "PRO" and not _is_pro_active(user_doc):
        await db.users.update_one(
            {"user_id": user_id}, {"$set": {"tier": "FREE"}}
        )
        user_doc["tier"] = "FREE"

    tier = (user_doc.get("tier") or "FREE").upper()
    count = int(user_doc.get("monthly_analyses_count") or 0)

    if tier == "FREE" and count >= FREE_MONTHLY_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Has agotado tus {FREE_MONTHLY_LIMIT} análisis gratuitos de este mes. "
                "Suscríbete a Pro por 5€/mes para análisis ilimitados."
            ),
        )
    return user_doc


async def increment_analysis_count(user_id: str) -> None:
    """Atomically bump the user's monthly counter (after a successful AI call)."""
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"monthly_analyses_count": 1},
            "$set": {"last_analysis_month": _current_month_utc()},
        },
    )


# Backwards-compat aliases so older routers keep working without a big refactor.
enforce_daily_limit = enforce_monthly_limit


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

    # Downgrade expired PRO users lazily on every auth check.
    if (user_doc.get("tier") or "FREE").upper() == "PRO" and not _is_pro_active(user_doc):
        await db.users.update_one(
            {"user_id": session_doc["user_id"]}, {"$set": {"tier": "FREE"}}
        )
        user_doc["tier"] = "FREE"

    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    if isinstance(user_doc.get("pro_expires_at"), str):
        try:
            user_doc["pro_expires_at"] = datetime.fromisoformat(user_doc["pro_expires_at"])
        except ValueError:
            user_doc["pro_expires_at"] = None
    user_doc.setdefault("mode", "professional")
    user_doc.setdefault("tier", "FREE")
    user_doc.setdefault("monthly_analyses_count", 0)
    user_doc.setdefault("last_analysis_month", None)
    user_doc.setdefault("pro_expires_at", None)
    user_doc.setdefault("stripe_customer_id", None)
    return User(**user_doc)
