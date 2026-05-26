"""
Generic article body fetcher for OSINT enrichment (Reuters, FA, GDELT snippets, etc.).
Uses trafilatura when available, BeautifulSoup fallback otherwise.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ca;q=0.8",
}

SKIP_HOSTS = frozenset(
    {
        "news.google.com",
        "www.google.com",
        "t.co",
        "twitter.com",
        "x.com",
        "facebook.com",
        "www.facebook.com",
        "instagram.com",
        "youtube.com",
        "www.youtube.com",
        "reddit.com",
        "www.reddit.com",
    }
)

_request_lock = asyncio.Lock()
_last_by_host: dict[str, float] = {}


def is_fetchable_url(url: str) -> bool:
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        return False
    try:
        host = urlparse(u).netloc.lower().replace("www.", "")
    except Exception:
        return False
    return host not in SKIP_HOSTS and "." in host


def _strip_html(html: str) -> str:
    if not html:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ")).strip()


def _extract_with_bs4(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    for selector in (
        "article",
        "[role=main]",
        "main",
        ".article-body",
        ".article-content",
        ".story-body",
        ".post-content",
        "#article-body",
    ):
        node = soup.select_one(selector)
        if node:
            text = _strip_html(str(node))
            if len(text) >= 120:
                return text
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = " ".join(p for p in paragraphs if len(p) > 40)
    return text.strip()


def _extract_text(html: str, url: str) -> tuple[str, str]:
    """Return (body, title)."""
    title = ""
    try:
        import trafilatura

        downloaded = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if downloaded and len(downloaded.strip()) >= 120:
            meta = trafilatura.extract_metadata(html, default_url=url)
            if meta and meta.title:
                title = meta.title.strip()
            return downloaded.strip(), title
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("trafilatura failed for %s: %s", url[:60], exc)

    body = _extract_with_bs4(html)
    soup = BeautifulSoup(html, "html.parser")
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = str(og["content"]).strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    return body, title


async def _throttle_host(url: str) -> None:
    host = urlparse(url).netloc.lower()
    interval = float(getattr(settings, "ARTICLE_FETCHER_RATE_LIMIT_SEC", 1.5))
    async with _request_lock:
        elapsed = time.monotonic() - _last_by_host.get(host, 0.0)
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
        _last_by_host[host] = time.monotonic()


async def fetch_article_body(url: str) -> dict[str, Any] | None:
    """
    Fetch and extract main article text from a public URL.
    Returns {url, title, body, provider} or None on failure.
    """
    url = (url or "").strip()
    if not is_fetchable_url(url):
        return None

    timeout = float(getattr(settings, "ARTICLE_FETCHER_TIMEOUT_SEC", 25.0))
    await _throttle_host(url)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            if "html" not in content_type and "text/" not in content_type:
                return None
            html = resp.text or ""
    except Exception as exc:
        logger.debug("Article fetch failed %s: %s", url[:70], exc)
        return None

    if len(html) < 200:
        return None

    body, title = _extract_text(html, url)
    if len(body.strip()) < 120:
        return None

    return {
        "url": url,
        "title": title,
        "body": body[:12000],
        "summary": body[:500],
        "provider": "article_fetcher",
        "enrichment_source": "article_fetcher",
    }


async def fetch_articles_batch(urls: list[str], *, max_items: int = 10) -> dict[str, dict[str, Any]]:
    """Fetch up to max_items unique URLs sequentially (rate-limited per host)."""
    out: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for url in urls:
        if len(out) >= max_items:
            break
        u = url.strip()
        if not u or u in seen:
            continue
        seen.add(u)
        article = await fetch_article_body(u)
        if article:
            out[u] = article
    return out
