"""
Nominatim (OpenStreetMap) API integration - Free geocoding
No API key required
"""
import httpx
from typing import Dict, Any, Optional, List

class NominatimAPIService:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.headers = {
            "User-Agent": "OSINT-Platform/1.0"  # Required by Nominatim
        }
    
    async def geocode(self, query: str, limit: int = 1) -> Dict[str, Any]:
        """Geocode a location name to coordinates"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": limit,
                        "addressdetails": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if not data or len(data) == 0:
                    return {
                        "status": "error",
                        "error": "Location not found",
                        "query": query,
                        "results": []
                    }
                
                results = []
                for item in data:
                    results.append({
                        "name": item.get("display_name", query),
                        "latitude": float(item.get("lat", 0)),
                        "longitude": float(item.get("lon", 0)),
                        "type": item.get("type", "unknown"),
                        "address": item.get("address", {}),
                        "importance": item.get("importance", 0)
                    })
                
                return {
                    "status": "success",
                    "query": query,
                    "results": results
                }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "query": query,
                    "results": []
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error inesperado: {str(e)}",
                    "query": query,
                    "results": []
                }
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Reverse geocode coordinates to location name"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/reverse",
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "json",
                        "addressdetails": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    return {
                        "status": "error",
                        "error": data.get("error", "Unknown error"),
                        "latitude": latitude,
                        "longitude": longitude
                    }
                
                address = data.get("address", {})
                return {
                    "status": "success",
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": data.get("display_name", ""),
                    "address": address,
                    "type": data.get("type", "unknown")
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "latitude": latitude,
                    "longitude": longitude
                }









