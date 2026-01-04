"""
Wayback Machine API integration - Archive.org historical data
"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

class WaybackAPIService:
    def __init__(self):
        self.base_url = "https://web.archive.org"
        self.cdx_url = "https://web.archive.org/cdx/search/cdx"
    
    async def get_snapshots(
        self,
        url: str,
        limit: int = 10,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get historical snapshots of a URL"""
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "url": url,
                    "output": "json",
                    "limit": limit
                }
                
                if from_date:
                    params["from"] = from_date
                if to_date:
                    params["to"] = to_date
                
                response = await client.get(
                    self.cdx_url,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                snapshots = []
                
                if len(data) > 1:  # First row is headers
                    for row in data[1:]:
                        if len(row) >= 3:
                            snapshots.append({
                                "timestamp": row[1],
                                "original": row[2],
                                "url": f"{self.base_url}/web/{row[1]}/{row[2]}"
                            })
                
                return {
                    "url": url,
                    "status": "success",
                    "snapshots": snapshots,
                    "total": len(snapshots)
                }
            except httpx.HTTPError as e:
                return {
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "snapshots": []
                }
            except Exception as e:
                return {
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "snapshots": []
                }
    
    async def get_available(
        self,
        url: str
    ) -> Dict[str, Any]:
        """Check if URL is available in Wayback Machine"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/web/{url}",
                    follow_redirects=True,
                    timeout=10.0
                )
                
                return {
                    "url": url,
                    "status": "success",
                    "available": response.status_code == 200,
                    "archive_url": str(response.url) if response.status_code == 200 else None
                }
            except Exception as e:
                return {
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "available": False
                }









