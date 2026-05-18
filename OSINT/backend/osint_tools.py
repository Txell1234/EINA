"""OSINT collection tools - mock/simulated for demo. Normalizes original_url per source."""
import json
from typing import Any, Optional
from datetime import datetime


def _normalize_original_url(source: str, raw: dict) -> Optional[str]:
    """Extract and normalize original URL from raw_data per source type."""
    if not raw:
        return None
    if source in ("news", "google_news"):
        items = raw.get("articles", raw.get("items", []))
        if items and isinstance(items, list):
            first = items[0] if items else {}
            return first.get("link") or first.get("url") or first.get("urlToImage")
        return raw.get("link") or raw.get("url")
    if source == "reddit":
        p = raw.get("data", raw) if isinstance(raw, dict) else {}
        return p.get("url") or p.get("permalink") or (f"https://reddit.com{p.get('permalink', '')}" if p.get("permalink") else None)
    if source in ("sherlock", "username"):
        results = raw.get("results", raw.get("accounts", {}))
        if isinstance(results, dict):
            for platform, data in list(results.items())[:1]:
                if isinstance(data, dict):
                    return data.get("url") or data.get("link")
        return raw.get("url")
    if source == "github":
        return raw.get("html_url") or raw.get("url") or raw.get("clone_url")
    if source in ("domain", "recon-ng", "whois", "dns"):
        domain = raw.get("domain", raw.get("query", ""))
        if domain:
            return f"https://{domain}" if not domain.startswith("http") else domain
        return raw.get("url")
    if source == "wayback":
        return raw.get("url") or raw.get("archived_url")
    return raw.get("url") or raw.get("link") or raw.get("original_url")


def collect_news(query: str) -> dict:
    """Mock Google News collection."""
    data = {
        "articles": [
            {"title": f"Notícia sobre {query}", "link": f"https://news.example.com/{query.replace(' ', '-')}", "publishedAt": datetime.utcnow().isoformat()},
        ]
    }
    return data


def collect_reddit(query: str) -> dict:
    """Mock Reddit collection."""
    slug = query.replace(" ", "_")[:30]
    return {"data": {"url": f"https://reddit.com/r/news/comments/{slug}", "permalink": f"/r/news/comments/{slug}"}}


def collect_sherlock(username: str) -> dict:
    """Mock Sherlock collection."""
    return {"results": {"twitter": {"url": f"https://twitter.com/{username}"}}}


def collect_github(query: str) -> dict:
    """Mock GitHub collection."""
    return {"html_url": f"https://github.com/{query}", "name": query}


def collect_domain(domain: str) -> dict:
    """Mock domain/Recon-ng collection."""
    return {"domain": domain, "query": domain}


def collect_osint(source_type: str, query: str) -> tuple[dict, str]:
    """Collect OSINT by source type. Returns (raw_data, source_name)."""
    q = query.strip()
    source_map = {
        "username": ("sherlock", collect_sherlock),
        "sherlock": ("sherlock", collect_sherlock),
        "news": ("news", collect_news),
        "google_news": ("news", collect_news),
        "reddit": ("reddit", collect_reddit),
        "github": ("github", collect_github),
        "domain": ("domain", collect_domain),
        "recon-ng": ("recon-ng", collect_domain),
        "whois": ("whois", collect_domain),
        "dns": ("dns", collect_domain),
        "wayback": ("wayback", lambda x: {"url": f"https://web.archive.org/web/*/{x}"}),
    }
    entry = source_map.get(source_type, ("unknown", lambda x: {"query": x}))
    source_name = entry[0]
    fn = entry[1]
    raw = fn(q) if callable(fn) else fn
    return raw, source_name
