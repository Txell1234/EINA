"""Helpers for geographic visualization of OSINT by provider."""
from __future__ import annotations

from typing import Any


def osint_provider_from_query_type(query_type: str) -> str:
    qt = (query_type or "").strip().lower()
    if qt.startswith("tavily"):
        return "tavily"
    if qt in ("gdelt", "gdelt_gfg"):
        return "gdelt"
    if qt == "google_news":
        return "google_news"
    if qt == "reddit":
        return "reddit"
    if qt.startswith("rss"):
        return "rss"
    if qt in ("nikkei", "bloomberg"):
        return qt
    return qt or "other"


def article_provider(article: dict[str, Any], fallback: str) -> str:
    raw = str(
        article.get("provider")
        or article.get("source")
        or article.get("enrichment_source")
        or ""
    ).lower()
    if raw.startswith("tavily"):
        return "tavily"
    if raw in ("gdelt", "google_news", "reddit", "rss", "nikkei", "bloomberg"):
        return raw
    return fallback


def bump_osint_source_counts(
    data: dict[str, Any] | None,
    provider: str,
    *,
    increment: int = 1,
) -> dict[str, Any]:
    base = dict(data or {})
    counts: dict[str, int] = dict(base.get("osint_sources") or {})
    key = provider or "other"
    counts[key] = counts.get(key, 0) + increment
    base["osint_sources"] = counts
    top = max(counts.items(), key=lambda x: x[1])[0] if counts else key
    base["primary_osint_source"] = top
    return base
