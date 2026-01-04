"""
Shodan API integration - Search for devices connected to the internet
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class ShodanAPIService:
    def __init__(self):
        self.base_url = "https://api.shodan.io"
        self.api_key = getattr(settings, "SHODAN_API_KEY", "")
        self.headers = {
            "User-Agent": "OSINT-Platform/1.0"
        }
    
    async def search(
        self,
        query: str,
        facets: Optional[str] = None,
        page: int = 1
    ) -> Dict[str, Any]:
        """Search Shodan"""
        if not self.api_key:
            return {
                "status": "error",
                "error": "Shodan requiere una cuenta de pago. Esta funcionalidad no está disponible actualmente. Para más información: https://account.shodan.io/register",
                "message": "Shodan requiere cuenta de pago",
                "results": []
            }
        
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "query": query,
                    "key": self.api_key,
                    "page": page
                }
                if facets:
                    params["facets"] = facets
                
                response = await client.get(
                    f"{self.base_url}/shodan/host/search",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "results": []
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "results": []
                }
    
    async def host_info(self, ip: str) -> Dict[str, Any]:
        """Get information about a specific host"""
        if not self.api_key:
            return {
                "status": "error",
                "error": "Shodan requiere una cuenta de pago. Esta funcionalidad no está disponible actualmente. Para más información: https://account.shodan.io/register",
                "message": "Shodan requiere cuenta de pago"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/shodan/host/{ip}",
                    params={"key": self.api_key},
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": str(e)
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e)
                }

