"""Skill / keyword normalisation helpers.

Deterministic: same input always produces same output. Pure functions.
"""
from __future__ import annotations

import re
from typing import Iterable, List


# Canonical aliases — keep this short and high-precision.
_ALIASES = {
    "react.js": "react",
    "reactjs": "react",
    "node.js": "node",
    "nodejs": "node",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "next",
    "nextjs": "next",
    "nuxt.js": "nuxt",
    "nuxtjs": "nuxt",
    "express.js": "express",
    "expressjs": "express",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "py": "python",
    "postgres": "postgresql",
    "postgre": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "aws": "aws",
    "ms sql": "sql server",
    "mssql": "sql server",
    "css3": "css",
    "html5": "html",
    "tailwindcss": "tailwind",
    "scss": "sass",
    "fastapi": "fastapi",
    "django rest framework": "drf",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "ux": "user experience",
    "ui": "user interface",
    "ci/cd": "cicd",
    "ci-cd": "cicd",
}


_PUNCT_RE = re.compile(r"[^\w\s.+#-]+")
_WS_RE = re.compile(r"\s+")


def normalize_skill(value: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, apply aliases."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    if s in _ALIASES:
        return _ALIASES[s]
    # Try a second pass without trailing version numbers (e.g. "python 3" -> "python").
    s_compact = re.sub(r"\s+\d+(\.\d+)?$", "", s)
    if s_compact in _ALIASES:
        return _ALIASES[s_compact]
    return s_compact or s


def normalize_skills_list(values: Iterable[str]) -> List[str]:
    """Normalise + deduplicate while preserving order."""
    seen = set()
    out: List[str] = []
    for v in values or []:
        n = normalize_skill(v)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def normalize_keyword(value: str) -> str:
    """Lighter normalisation for free-text keywords."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = _WS_RE.sub(" ", s)
    return s
