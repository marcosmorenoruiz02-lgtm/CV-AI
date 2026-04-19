"""POST /api/job/import — scrape a public job posting URL → structured JSON via LLM."""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException

from deps import User, get_current_user
from schemas.job import JobImportInput, StructuredJob
from services.llm.client import call_json
from services.llm.prompts import JOB_EXTRACTION_SYSTEM

router = APIRouter(prefix="/api/job", tags=["job-import"])
logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36"
)
URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)


class JobImportResponse(StructuredJob):
    source_url: str
    raw_text_excerpt: Optional[str] = None


async def _fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"La URL devolvió HTTP {r.status_code}")
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype and "text" not in ctype:
            raise HTTPException(status_code=400, detail="La URL no devuelve HTML/texto")
        return r.text


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "iframe"]):
        tag.decompose()
    # Prefer main / article when present.
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@router.post("/import", response_model=JobImportResponse)
async def import_job(payload: JobImportInput, _: User = Depends(get_current_user)):
    url = (payload.url or "").strip()
    if not url or not URL_REGEX.match(url):
        raise HTTPException(status_code=400, detail="URL inválida (debe empezar por http(s)://)")

    try:
        html = await _fetch_html(url)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fetch failed")
        raise HTTPException(status_code=400, detail=f"No se pudo descargar la URL: {e}")

    text = _clean_text(html)
    if len(text) < 200:
        raise HTTPException(
            status_code=422,
            detail="La página no contiene suficiente texto para analizar la oferta.",
        )

    excerpt = text[:18000]
    parsed = await call_json(
        JOB_EXTRACTION_SYSTEM,
        f"TEXTO DE LA OFERTA (URL: {url}):\n\n{excerpt}",
        fallback={},
    )
    if not isinstance(parsed, dict):
        parsed = {}

    skills_raw = parsed.get("skills") or []
    skills = []
    for s in skills_raw:
        if isinstance(s, dict) and s.get("name"):
            try:
                skills.append({"name": str(s["name"]), "weight": float(s.get("weight") or 1.0)})
            except Exception:
                continue
        elif isinstance(s, str):
            skills.append({"name": s, "weight": 1.0})

    job = StructuredJob(
        title=parsed.get("title") or "",
        company=parsed.get("company") or "",
        skills=skills,
        required_years=float(parsed.get("required_years") or 0),
        education_required=parsed.get("education_required") or "",
        keywords=[str(k) for k in (parsed.get("keywords") or []) if k],
        role_summary=parsed.get("role_summary") or "",
    )

    return JobImportResponse(
        **job.model_dump(),
        source_url=url,
        raw_text_excerpt=text[:1500],
    )
