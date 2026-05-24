"""
GDELT Project API - Global events and geopolitical data
Free, no API key required. gdeltproject.org
"""
import asyncio
import logging
import time
from typing import Any

import httpx

from services.osint_data_utils import extract_search_keywords, normalize_search_query

logger = logging.getLogger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2"
MIN_REQUEST_INTERVAL_SEC = 2.5
CACHE_TTL_SEC = 300
MAX_RETRIES = 3
RETRY_DELAYS_SEC = (5, 15, 30)

_last_request_at = 0.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


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
        if result.get("count", 0) == 0 and query != raw_query:
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

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                await _throttle()
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.get(url, params=params)

                    if resp.status_code == 429:
                        delay = RETRY_DELAYS_SEC[min(attempt, len(RETRY_DELAYS_SEC) - 1)]
                        logger.warning(
                            "GDELT 429 (intent %s/%s), esperant %ss…",
                            attempt + 1,
                            MAX_RETRIES,
                            delay,
                        )
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(delay)
                            continue
                        return {
                            "status": "error",
                            "error": (
                                "GDELT ha limitat les peticions (429). "
                                "Espera 1-2 minuts abans de tornar a cercar o prova amb menys dies."
                            ),
                            "message": "Rate limit GDELT",
                            "count": 0,
                            "articles": [],
                            "retry_after_sec": delay,
                        }

                    resp.raise_for_status()
                    data = resp.json()
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
                    }
                    _set_cache(key, result)
                    return result

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS_SEC[attempt])
                    continue
                logger.error("GDELT HTTP %s: %s", e.response.status_code, e)
                return {
                    "status": "error",
                    "error": f"GDELT ha retornat error HTTP {e.response.status_code}.",
                    "message": str(e),
                    "count": 0,
                    "articles": [],
                }
            except Exception as e:
                last_error = e
                logger.error("GDELT error: %s", e)
                break

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
