"""Shared dependencies (auth + db + settings) reused across routers.

Centralised here to avoid circular imports with server.py.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
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
    mode: str = "professional"  # "junior" | "professional"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    return User(**user_doc)
