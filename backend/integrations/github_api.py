"""
GitHub API integration
"""
import httpx
from typing import Dict, Any
from app.config import settings

class GitHubAPIService:
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.token = getattr(settings, "GITHUB_TOKEN", "")
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    async def search(
        self,
        query: str,
        type: str = "repositories",
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search GitHub"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/{type}",
                    params={
                        "q": query,
                        "per_page": per_page
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
                    "items": []
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "items": []
                }









