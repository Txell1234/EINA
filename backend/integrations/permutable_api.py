"""
Permutable AI API integration - Geopolitical data and sentiment
Note: Requires premium account or free trial. Contact enquiries@permutable.ai
"""
import httpx
from typing import Dict, Any, Optional, List
from app.config import settings
from datetime import datetime

class PermutableAPIService:
    def __init__(self):
        self.base_url = "https://api.permutable.ai"  # API endpoint (to be confirmed)
        self.api_key = getattr(settings, "PERMUTABLE_API_KEY", "").strip()
        # Note: Permutable AI requires account setup and API key from enquiries@permutable.ai
    
    async def get_geopolitical_sentiment(
        self,
        country: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get geopolitical sentiment data"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-permutable-api-key":
            return {
                "status": "error",
                "error": "PERMUTABLE_API_KEY no está configurada. Permutable AI requiere una cuenta premium o trial. Contacta: enquiries@permutable.ai",
                "message": "API key no configurada",
                "info": "Permutable AI ofrece datos geopolíticos premium. Solicita un trial gratuito en https://permutable.ai/datasets-geopolitical-data/"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "token": self.api_key
                }
                if country:
                    params["country"] = country
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date
                
                # Note: Actual endpoint structure to be confirmed with Permutable AI
                response = await client.get(
                    f"{self.base_url}/geopolitical/sentiment",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "data": data
                }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "message": "Error de conexión"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error obteniendo datos geopolíticos"
                }
    
    async def get_country_profile(self, country: str) -> Dict[str, Any]:
        """Get country macro profile and geopolitical data"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-permutable-api-key":
            return {
                "status": "error",
                "error": "PERMUTABLE_API_KEY no está configurada. Permutable AI requiere una cuenta premium o trial.",
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/geopolitical/country/{country}",
                    params={"token": self.api_key},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "country": country,
                    "profile": data
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error obteniendo perfil de país"
                }
    
    async def get_geopolitical_events(
        self,
        location: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get geopolitical events (tariffs, sanctions, wars, etc.)"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-permutable-api-key":
            return {
                "status": "error",
                "error": "PERMUTABLE_API_KEY no está configurada. Permutable AI requiere una cuenta premium o trial.",
                "message": "API key no configurada",
                "events": []
            }
        
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "token": self.api_key,
                    "limit": limit
                }
                if location:
                    params["location"] = location
                if topic:
                    params["topic"] = topic
                
                response = await client.get(
                    f"{self.base_url}/geopolitical/events",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "events": data.get("events", []),
                    "total": len(data.get("events", []))
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error obteniendo eventos geopolíticos",
                    "events": []
                }









