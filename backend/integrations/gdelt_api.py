"""
GDELT Project API - Global events and geopolitical data
Free, no API key required. gdeltproject.org
"""
import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import quote_plus

import httpx

from services.osint_data_utils import extract_search_keywords, normalize_search_query

logger = logging.getLogger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
# GDELT doc API: màxim ~1 petició cada 5 segons (documentació oficial)
MIN_REQUEST_INTERVAL_SEC = 5.5
CACHE_TTL_SEC = 300
MAX_RETRIES = 3
RETRY_DELAYS_SEC = (8, 20, 40)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

_last_request_at = 0.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_request_lock = asyncio.Lock()


def _cache_key(query: str, days: int, max_results: int) -> str:
    return f"{query.strip().lower()}|{days}|{max_results}"


def _get_cached(key: str) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.monotonic() - ts > CACHE_TTL_SEC:
        _cache.pop(key, None)
        return None
    return payload


def _set_cache(key: str, payload: dict[str, Any]) -> None:
    _cache[key] = (time.monotonic(), payload)


async def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_REQUEST_INTERVAL_SEC:
        await asyncio.sleep(MIN_REQUEST_INTERVAL_SEC - elapsed)
    _last_request_at = time.monotonic()


def _is_rate_limited(status_code: int, body: str) -> bool:
    if status_code == 429:
        return True
    lower = body.lower()
    return "please limit requests" in lower or "rate limit" in lower


async def _fetch_google_news_fallback(query: str, max_results: int) -> dict[str, Any]:
    """Fallback quan GDELT no respon o limita peticions."""
    try:
        import feedparser
    except ImportError:
        return {"status": "error", "count": 0, "articles": []}

    url = (
        f"{GOOGLE_NEWS_RSS}?q={quote_plus(query)}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=DEFAULT_HEADERS)
            resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:max_results]:
            publisher = getattr(entry, "source", None)
            domain = ""
            if isinstance(publisher, dict):
                domain = str(publisher.get("title") or publisher.get("href") or "Google News")
            articles.append(
                {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "date": getattr(entry, "published", "") or getattr(entry, "updated", ""),
                    "source": domain or "Google News",
                    "language": "",
                    "tone": "",
                }
            )
        if not articles:
            return {"status": "error", "count": 0, "articles": []}
        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "google_news_rss",
            "fallback": True,
            "message": "GDELT no disponible — resultats via Google News RSS",
        }
    except Exception as exc:
        logger.warning("Google News fallback failed: %s", exc)
        return {"status": "error", "count": 0, "articles": [], "message": str(exc)}


class GDELTAPIService:
    async def search_events(
        self, query: str, days: int = 7, max_results: int = 50
    ) -> dict[str, Any]:
        raw_query = (query or "").strip()
        if not raw_query:
            return {
                "status": "error",
                "error": "La consulta GDELT no pot estar buida.",
                "message": "Consulta buida",
                "count": 0,
                "articles": [],
            }

        query = extract_search_keywords(raw_query) if len(raw_query) > 80 else normalize_search_query(raw_query)
        days = max(1, min(int(days), 90))
        max_results = max(1, min(int(max_results), 75))

        result = await self._fetch(query, days, max_results)
        if result.get("count", 0) == 0 and query != raw_query and result.get("status") == "success":
            logger.info("GDELT 0 resultats amb query normalitzada, reintent amb keywords…")
            alt = extract_search_keywords(raw_query)
            if alt and alt != query:
                result = await self._fetch(alt, days, max_results)
        return result

    async def _fetch(self, query: str, days: int, max_results: int) -> dict[str, Any]:
        key = _cache_key(query, days, max_results)
        cached = _get_cached(key)
        if cached:
            logger.info("GDELT cache hit for query=%r", query[:60])
            return {**cached, "cached": True}

        url = f"{GDELT_BASE}/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_results,
            "timespan": f"{days}days",
            "format": "json",
            "sort": "DateDesc",
        }

        last_error: Exception | str | None = None
        for attempt in range(MAX_RETRIES):
            try:
                async with _request_lock:
                    await _throttle()
                    async with httpx.AsyncClient(
                        timeout=45.0,
                        follow_redirects=True,
                        headers=DEFAULT_HEADERS,
                    ) as client:
                        resp = await client.get(url, params=params)
                        body = resp.text or ""

                if _is_rate_limited(resp.status_code, body):
                    delay = RETRY_DELAYS_SEC[min(attempt, len(RETRY_DELAYS_SEC) - 1)]
                    logger.warning(
                        "GDELT rate limit (intent %s/%s), esperant %ss…",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                    )
                    last_error = "rate_limit"
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(delay)
                        continue
                    break

                resp.raise_for_status()
                try:
                    data = resp.json()
                except json.JSONDecodeError as exc:
                    last_error = exc
                    logger.error("GDELT resposta no JSON: %s", body[:200])
                    break

                articles = data.get("articles") or []
                result = {
                    "status": "success",
                    "query_used": query,
                    "count": len(articles),
                    "articles": [
                        {
                            "title": a.get("title", ""),
                            "url": a.get("url", ""),
                            "date": a.get("seendate", ""),
                            "source": a.get("domain", ""),
                            "language": a.get("language", ""),
                            "tone": a.get("tone", ""),
                        }
                        for a in articles
                    ],
                    "provider": "gdelt",
                }
                _set_cache(key, result)
                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS_SEC[attempt])
                    continue
                logger.error("GDELT HTTP %s: %s", e.response.status_code, e)
                break
            except Exception as e:
                last_error = e
                logger.error("GDELT error: %s", e)
                break

        fallback = await _fetch_google_news_fallback(query, max_results)
        if fallback.get("status") == "success" and fallback.get("articles"):
            result = {
                **fallback,
                "query_used": query,
                "gdelt_error": (
                    "GDELT ha limitat les peticions (429)."
                    if last_error == "rate_limit"
                    else "No s'ha pogut connectar amb GDELT."
                ),
            }
            _set_cache(key, result)
            return result

        if last_error == "rate_limit":
            return {
                "status": "error",
                "error": (
                    "GDELT ha limitat les peticions (429). "
                    "Espera 1-2 minuts abans de tornar a cercar o prova amb menys dies."
                ),
                "message": "Rate limit GDELT",
                "count": 0,
                "articles": [],
                "retry_after_sec": RETRY_DELAYS_SEC[-1],
            }

        return {
            "status": "error",
            "error": (
                "No s'ha pogut connectar amb GDELT. "
                "Torna-ho a provar en uns minuts o utilitza una altra font (RSS)."
            ),
            "message": str(last_error) if last_error else "Error desconegut",
            "count": 0,
            "articles": [],
        }

    async def search_by_country(self, country_code: str, days: int = 7) -> dict[str, Any]:
        return await self.search_events(f"sourcecountry:{country_code}", days=days)
