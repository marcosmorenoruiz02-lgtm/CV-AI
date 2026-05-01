"""Shared HTTP scraper for job postings (used by /api/job/import and /api/quick-analyze)."""
from __future__ import annotations

import re
from typing import Tuple

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36"
)

URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)


class ScrapeError(Exception):
    """Raised when a URL cannot be fetched or cleaned."""


async def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
    if r.status_code >= 400:
        raise ScrapeError(f"La URL devolvió HTTP {r.status_code}")
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise ScrapeError("La URL no devuelve HTML/texto")
    return r.text


def clean_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "iframe", "aside"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def fetch_and_clean(url: str) -> Tuple[str, str]:
    """Fetch a URL and return (clean_text, original_url). Raises ScrapeError on failure."""
    url = (url or "").strip()
    if not url or not URL_REGEX.match(url):
        raise ScrapeError("URL inválida (debe empezar por http(s)://)")
    html = await fetch_html(url)
    text = clean_html_text(html)
    if len(text) < 200:
        raise ScrapeError("La página no contiene suficiente texto para analizar la oferta.")
    return text, url
