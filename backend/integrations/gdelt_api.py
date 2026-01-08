"""
GDELT API integration for global event/news monitoring
Documentation: https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
"""
from typing import Dict, Any, Optional
import httpx


class GDELTAPIService:
    def __init__(self):
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def search(
        self,
        query: str,
        max_records: int = 50,
        mode: str = "artlist",
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search GDELT documents with optional date range (YYYYMMDDHHMMSS)"""
        try:
            params = {
                "query": query,
                "format": "json",
                "mode": mode,
                "maxrecords": max_records
            }
            if start_datetime:
                params["startdatetime"] = start_datetime
            if end_datetime:
                params["enddatetime"] = end_datetime

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            return {
                "status": "success",
                "articles": data.get("articles", []),
                "count": len(data.get("articles", [])),
                "query": query,
            }
        except httpx.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP error: {str(e)}",
                "articles": []
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "articles": []
            }
