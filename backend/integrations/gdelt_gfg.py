"""
GDELT Global Frontpage Graph (GFG) — editorial prominence from news homepages.

Scans ~50k news homepages hourly and records link position as an importance signal.
https://blog.gdeltproject.org/announcing-gdelt-global-frontpage-graph-gfg/
"""
from __future__ import annotations

import asyncio
import gzip
import io
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from services.osint_data_utils import extract_search_keywords, normalize_search_query

logger = logging.getLogger(__name__)

GFG_LASTUPDATE = "http://data.gdeltproject.org/gdeltv3/gfg/alpha/lastupdate.txt"
GFG_BASE = "http://data.gdeltproject.org/gdeltv3/gfg/alpha/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}

# GFG hourly files can exceed 10M rows — cap scan volume for responsiveness.
MAX_LINES_SCANNED = 750_000
CACHE_TTL_SEC = 1800

_file_url_cache: tuple[float, str] | None = None
_search_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _parse_gfg_line(line: str) -> dict[str, Any] | None:
    """Parse one tab-delimited GFG row."""
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 6:
        return None
    try:
        link_percent = float(parts[3])
    except ValueError:
        link_percent = 100.0
    return {
        "date": parts[0],
        "from_frontpage_url": parts[1],
        "link_id": parts[2],
        "link_percent_max_id": link_percent,
        "url": parts[4],
        "link_text": parts[5],
    }


def _query_terms(query: str) -> list[str]:
    normalized = normalize_search_query(query, max_len=120)
    keywords = extract_search_keywords(normalized) if len(normalized) > 80 else normalized
    terms = [t.lower() for t in re.split(r"\s+", keywords) if len(t) >= 2]
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out or [normalized.lower()] if normalized else []


def _matches_terms(row: dict[str, Any], terms: list[str], domain_filter: str) -> bool:
    haystack = f"{row.get('url', '')} {row.get('link_text', '')}".lower()
    if domain_filter:
        host = urlparse(str(row.get("url") or "")).netloc.lower()
        if domain_filter not in host:
            return False
    return any(term in haystack for term in terms)


def _row_to_article(row: dict[str, Any]) -> dict[str, Any]:
    link_percent = float(row.get("link_percent_max_id") or 100)
    title = str(row.get("link_text") or "").strip()
    url = str(row.get("url") or "").strip()
    homepage = str(row.get("from_frontpage_url") or "").strip()
    source = urlparse(homepage).netloc or homepage
    prominence = max(0.0, min(100.0, 100.0 - link_percent))
    return {
        "title": title or url,
        "url": url,
        "date": str(row.get("date") or ""),
        "source": source,
        "summary": f"Portada {source} — posició relativa {link_percent:.1f}%",
        "link_text": title,
        "from_frontpage_url": homepage,
        "link_percent_max_id": link_percent,
        "frontpage_score": round(prominence, 2),
        "importance_score": round(prominence, 2),
    }


def _scan_gfg_gzip(
    gz_bytes: bytes,
    terms: list[str],
    domain_filter: str,
    max_results: int,
) -> tuple[list[dict[str, Any]], int]:
    """Stream-parse GFG gzip in a worker thread; return best articles by prominence."""
    best_by_url: dict[str, dict[str, Any]] = {}
    lines_scanned = 0

    with gzip.GzipFile(fileobj=io.BytesIO(gz_bytes)) as gz:
        text_stream = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
        for line in text_stream:
            lines_scanned += 1
            if lines_scanned > MAX_LINES_SCANNED:
                break
            if not line.strip():
                continue
            row = _parse_gfg_line(line)
            if not row or not row.get("url"):
                continue
            if not _matches_terms(row, terms, domain_filter):
                continue

            article = _row_to_article(row)
            url = article["url"]
            existing = best_by_url.get(url)
            if existing is None or article["frontpage_score"] > existing["frontpage_score"]:
                best_by_url[url] = article

            if len(best_by_url) >= max_results * 3 and lines_scanned > 50_000:
                # Enough candidates found early — stop scanning to save time.
                break

    articles = sorted(
        best_by_url.values(),
        key=lambda a: (-a["frontpage_score"], a.get("title", "")),
    )[:max_results]
    return articles, lines_scanned


async def _get_latest_file_url(client: httpx.AsyncClient) -> str:
    global _file_url_cache
    now = time.monotonic()
    if _file_url_cache and now - _file_url_cache[0] < CACHE_TTL_SEC:
        return _file_url_cache[1]

    resp = await client.get(GFG_LASTUPDATE, headers=DEFAULT_HEADERS, timeout=20.0)
    resp.raise_for_status()
    filename = resp.text.strip().splitlines()[-1].strip()
    if not filename.endswith(".LINKS.TXT.gz"):
        filename = f"{filename}.LINKS.TXT.gz" if filename else ""
    if not filename:
        raise ValueError("GFG lastupdate.txt buit o invàlid")
    url = filename if filename.startswith("http") else f"{GFG_BASE}{filename}"
    _file_url_cache = (now, url)
    return url


class GDELTGFGService:
    """Search GDELT Global Frontpage Graph for editorial prominence signals."""

    async def search_frontpage(
        self,
        query: str,
        *,
        max_results: int = 40,
        domain: str = "",
    ) -> dict[str, Any]:
        raw_query = (query or "").strip()
        if not raw_query:
            return {
                "status": "error",
                "error": "La consulta GFG no pot estar buida.",
                "count": 0,
                "articles": [],
            }

        max_results = max(1, min(int(max_results), 100))
        domain_filter = domain.strip().lower().lstrip("www.")
        terms = _query_terms(raw_query)
        cache_key = f"{raw_query.lower()}|{max_results}|{domain_filter}"
        cached = _search_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_SEC:
            return {**cached[1], "cached": True}

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                file_url = await _get_latest_file_url(client)
                logger.info("GFG descarregant %s (terms=%s)", file_url, terms[:5])
                resp = await client.get(file_url, headers=DEFAULT_HEADERS, timeout=180.0)
                resp.raise_for_status()
                gz_bytes = resp.content

            articles, lines_scanned = await asyncio.to_thread(
                _scan_gfg_gzip,
                gz_bytes,
                terms,
                domain_filter,
                max_results,
            )

            result = {
                "status": "success",
                "query_used": " ".join(terms),
                "count": len(articles),
                "articles": articles,
                "provider": "gdelt_gfg",
                "gfg_file": file_url,
                "lines_scanned": lines_scanned,
                "message": (
                    f"{len(articles)} enllaços destacats a portades "
                    f"(escanejades {lines_scanned:,} files)"
                    if articles
                    else "Cap coincidència a la darrera instantània de portades GFG"
                ),
            }
            _search_cache[cache_key] = (time.monotonic(), result)
            return result

        except httpx.HTTPStatusError as exc:
            logger.error("GFG HTTP error: %s", exc)
            return {
                "status": "error",
                "error": f"Error descarregant GFG ({exc.response.status_code})",
                "count": 0,
                "articles": [],
            }
        except Exception as exc:
            logger.error("GFG error: %s", exc)
            return {
                "status": "error",
                "error": "No s'ha pogut processar el fitxer GFG.",
                "message": str(exc),
                "count": 0,
                "articles": [],
            }

    async def enrich_urls(self, urls: list[str]) -> dict[str, dict[str, Any]]:
        """
        Look up frontpage prominence for specific URLs in the latest GFG snapshot.
        Returns {url: {frontpage_score, from_frontpage_url, link_text}}.
        """
        clean_urls = [u.strip() for u in urls if u and u.strip()]
        if not clean_urls:
            return {}

        url_set = set(clean_urls)
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                file_url = await _get_latest_file_url(client)
                resp = await client.get(file_url, headers=DEFAULT_HEADERS, timeout=180.0)
                resp.raise_for_status()
                gz_bytes = resp.content

            found: dict[str, dict[str, Any]] = {}

            def _scan_urls() -> None:
                with gzip.GzipFile(fileobj=io.BytesIO(gz_bytes)) as gz:
                    text_stream = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
                    for i, line in enumerate(text_stream):
                        if i > MAX_LINES_SCANNED:
                            break
                        row = _parse_gfg_line(line)
                        if not row:
                            continue
                        url = str(row.get("url") or "")
                        if url not in url_set:
                            continue
                        article = _row_to_article(row)
                        prev = found.get(url)
                        if prev is None or article["frontpage_score"] > prev["frontpage_score"]:
                            found[url] = {
                                "frontpage_score": article["frontpage_score"],
                                "from_frontpage_url": article["from_frontpage_url"],
                                "link_text": article.get("link_text") or article.get("title"),
                                "link_percent_max_id": article["link_percent_max_id"],
                            }
                        if len(found) >= len(url_set):
                            break

            await asyncio.to_thread(_scan_urls)
            return found

        except Exception as exc:
            logger.warning("GFG enrich_urls failed: %s", exc)
            return {}
