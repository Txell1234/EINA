"""
Reddit API integration
"""
import httpx
from typing import Dict, Any, Optional

class RedditAPIService:
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {
            "User-Agent": "OSINT-Platform/1.0"
        }
    
    async def search(
        self,
        query: str,
        subreddit: Optional[str] = None,
        limit: int = 25
    ) -> Dict[str, Any]:
        """Search Reddit posts"""
        async with httpx.AsyncClient() as client:
            try:
                if subreddit:
                    url = f"{self.base_url}/r/{subreddit}/search.json"
                else:
                    url = f"{self.base_url}/search.json"
                
                response = await client.get(
                    url,
                    params={
                        "q": query,
                        "limit": limit,
                        "sort": "relevance"
                    },
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "data": []
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "data": []
                }









