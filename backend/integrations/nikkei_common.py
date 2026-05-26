"""Shared helpers for Nikkei Asia integrations."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

NIKKEI_HOSTS = ("asia.nikkei.com", "www.asia.nikkei.com")


def is_nikkei_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in NIKKEI_HOSTS)


def normalize_article(raw: dict[str, Any], *, provider: str) -> dict[str, Any]:
    title = str(
        raw.get("title")
        or raw.get("headline")
        or raw.get("name")
        or ""
    ).strip()
    url = str(raw.get("url") or raw.get("link") or "").strip()
    body = str(
        raw.get("text")
        or raw.get("body")
        or raw.get("content")
        or raw.get("articleText")
        or raw.get("article_text")
        or ""
    ).strip()
    authors = raw.get("authors") or raw.get("author") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(a) for a in authors if a)
    date = str(
        raw.get("publishedAt")
        or raw.get("published_at")
        or raw.get("date")
        or raw.get("published")
        or ""
    ).strip()
    return {
        "title": title,
        "url": url,
        "date": date,
        "source": "Nikkei Asia",
        "summary": body[:500] if body else title,
        "body": body,
        "authors": str(authors),
        "language": "en",
        "provider": provider,
    }
