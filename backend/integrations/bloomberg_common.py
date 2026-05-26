"""Shared helpers for Bloomberg integrations."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

BLOOMBERG_HOSTS = (
    "bloomberg.com",
    "www.bloomberg.com",
    "feeds.bloomberg.com",
)


def is_bloomberg_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().lstrip("www.")
    return any(host == h or host.endswith("." + h) for h in BLOOMBERG_HOSTS)


def normalize_article(raw: dict[str, Any], *, provider: str = "bloomberg_own") -> dict[str, Any]:
    title = str(
        raw.get("title")
        or raw.get("headline")
        or ""
    ).strip()
    url = str(raw.get("url") or raw.get("link") or "").strip()
    body = str(
        raw.get("body")
        or raw.get("text")
        or raw.get("content")
        or raw.get("summary")
        or ""
    ).strip()
    authors = raw.get("authors") or raw.get("author") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(a) for a in authors if a)
    date = str(
        raw.get("date")
        or raw.get("published")
        or raw.get("publishedAt")
        or ""
    ).strip()
    edition = str(raw.get("edition") or "").strip()
    section = str(raw.get("section") or raw.get("category") or "").strip()
    return {
        "title": title,
        "url": url,
        "date": date,
        "source": "Bloomberg",
        "summary": body[:500] if body else title,
        "body": body,
        "authors": str(authors),
        "language": "en",
        "edition": edition,
        "section": section,
        "provider": provider,
    }
