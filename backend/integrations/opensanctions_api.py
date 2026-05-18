"""
OpenSanctions API - Sanctions lists from 100+ governments
Free for non-commercial use. opensanctions.org/api
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENSANCTIONS_BASE = "https://api.opensanctions.org"


class OpenSanctionsService:
    async def search_entity(self, query: str, schema: str = "Thing") -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{OPENSANCTIONS_BASE}/search/{schema}",
                    params={"q": query, "limit": 20},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "status": "success",
                    "total": data.get("total", {}).get("value", 0),
                    "results": [
                        {
                            "id": r.get("id", ""),
                            "name": r.get("caption", ""),
                            "schema": r.get("schema", ""),
                            "datasets": r.get("datasets", []),
                            "score": r.get("score", 0),
                            "properties": r.get("properties", {}),
                        }
                        for r in data.get("results", [])
                    ],
                }
        except Exception as e:
            logger.error("OpenSanctions error: %s", e)
            return {"status": "error", "message": str(e)}

    async def check_entity(self, name: str) -> dict[str, Any]:
        result = await self.search_entity(name)
        if result.get("status") == "error":
            return result
        is_sanctioned = result.get("total", 0) > 0
        return {
            "status": "success",
            "entity": name,
            "is_sanctioned": is_sanctioned,
            "matches": result.get("total", 0),
            "top_matches": result.get("results", [])[:3],
        }
