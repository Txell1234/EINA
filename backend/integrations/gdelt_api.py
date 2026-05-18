"""
GDELT Project API - Global events and geopolitical data
Free, no API key required. gdeltproject.org
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2"


class GDELTAPIService:
    async def search_events(
        self, query: str, days: int = 7, max_results: int = 50
    ) -> dict[str, Any]:
        url = f"{GDELT_BASE}/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_results,
            "timespan": f"{days}days",
            "format": "json",
            "sort": "DateDesc",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                return {
                    "status": "success",
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
        except Exception as e:
            logger.error("GDELT error: %s", e)
            return {"status": "error", "message": str(e), "count": 0, "articles": []}

    async def search_by_country(self, country_code: str, days: int = 7) -> dict[str, Any]:
        return await self.search_events(f"sourcecountry:{country_code}", days=days)
