"""Shared HTTP scraper for job postings.

Improvements over a naive scraper:
- Tries JSON-LD JobPosting schema first (used by Indeed, Glassdoor, many boards).
- Detects auth walls / cookie walls / cloudflare blocks and surfaces a human-friendly error.
- Falls back to cleaned <main>/<article> text otherwise.
"""
from __future__ import annotations

import json
import re
from typing import List, Tuple

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36"
)

URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)

# Phrases that signal we're seeing an auth/cookie wall, not a job.
_BLOCK_PATTERNS = [
    r"\bsign\s*in\s*to\s+linkedin\b",
    r"\bjoin\s+now\b.*linkedin",
    r"\bjoin\s+linkedin\b",
    r"please\s+enable\s+javascript",
    r"are\s+you\s+a\s+human\??",
    r"\bcaptcha\b",
    r"access\s+denied",
    r"acceptar?\s+cookies",
    r"checking\s+your\s+browser",
]
_BLOCK_RE = re.compile("|".join(_BLOCK_PATTERNS), re.IGNORECASE)


class ScrapeError(Exception):
    """Raised when a URL cannot be fetched or cleaned."""


async def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
    if r.status_code == 403 or r.status_code == 401:
        raise ScrapeError(
            "Esta web bloquea el acceso automático. Copia y pega el texto de la oferta."
        )
    if r.status_code == 429:
        raise ScrapeError("La web nos pidió esperar (demasiadas peticiones). Pega el texto.")
    if r.status_code >= 400:
        raise ScrapeError(f"La URL devolvió un error {r.status_code}.")
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise ScrapeError("La URL no devuelve una página normal de oferta.")
    return r.text


def _extract_json_ld_job(soup: BeautifulSoup) -> str:
    """Look for <script type='application/ld+json'> with @type=JobPosting and return a clean text."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type") or item.get("type")
            types = t if isinstance(t, list) else [t]
            if not any(str(x).lower() == "jobposting" for x in types):
                continue
            parts: List[str] = []
            if item.get("title"):
                parts.append(f"Puesto: {item['title']}")
            org = item.get("hiringOrganization") or {}
            if isinstance(org, dict) and org.get("name"):
                parts.append(f"Empresa: {org['name']}")
            loc = item.get("jobLocation") or {}
            if isinstance(loc, list) and loc:
                loc = loc[0]
            if isinstance(loc, dict):
                addr = loc.get("address") or {}
                if isinstance(addr, dict):
                    city = addr.get("addressLocality")
                    country = addr.get("addressCountry")
                    if city or country:
                        parts.append(f"Ubicación: {city or ''} {country or ''}".strip())
            if item.get("employmentType"):
                et = item["employmentType"]
                parts.append(f"Tipo: {et if isinstance(et, str) else ', '.join(et)}")
            desc = item.get("description") or ""
            if desc:
                # description is often HTML
                desc_text = BeautifulSoup(str(desc), "lxml").get_text(separator="\n", strip=True)
                parts.append("\n" + desc_text)
            if item.get("qualifications"):
                parts.append(f"\nRequisitos:\n{item['qualifications']}")
            if item.get("responsibilities"):
                parts.append(f"\nResponsabilidades:\n{item['responsibilities']}")
            if item.get("skills"):
                sk = item["skills"]
                parts.append(f"\nSkills: {sk if isinstance(sk, str) else ', '.join(sk)}")
            return "\n".join(p for p in parts if p)
    return ""


def _clean_main_text(soup: BeautifulSoup) -> str:
    for tag in soup(
        ["script", "style", "noscript", "header", "footer", "nav", "form", "iframe", "aside"]
    ):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_blocked(text: str) -> bool:
    """Heuristic: short text with auth-wall keywords is an auth wall."""
    if not text:
        return True
    short = len(text) < 400
    has_block_phrase = bool(_BLOCK_RE.search(text))
    if has_block_phrase and short:
        return True
    # LinkedIn guest pages often ramble about "Welcome back" with no actual job description.
    li_signals = sum(
        1
        for kw in ("LinkedIn", "Sign in", "Join now", "Forgot password", "Continue with Google")
        if kw.lower() in text.lower()
    )
    if li_signals >= 3 and "responsabilidad" not in text.lower() and "requisit" not in text.lower():
        return True
    return False


async def fetch_and_clean(url: str) -> Tuple[str, str]:
    """Fetch a URL and return (clean_text, original_url). Raises ScrapeError on failure."""
    url = (url or "").strip()
    if not url or not URL_REGEX.match(url):
        raise ScrapeError("La dirección no es válida (debe empezar por http:// o https://).")
    html = await fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # 1) Try structured data first.
    structured = _extract_json_ld_job(soup)
    if structured and len(structured) > 200:
        return structured, url

    # 2) Fallback to cleaned visible text.
    text = _clean_main_text(soup)

    if _is_blocked(text):
        raise ScrapeError(
            "Esta web (LinkedIn, Indeed u otra) nos pide iniciar sesión para ver la oferta. "
            "Cópiala y pégala como texto y la analizamos."
        )
    if len(text) < 200:
        raise ScrapeError("La página no tiene texto suficiente. Pega el texto de la oferta.")
    return text, url
