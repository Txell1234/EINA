"""
Finnhub API integration - Free financial data
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class FinnhubAPIService:
    def __init__(self):
        self.base_url = "https://finnhub.io/api/v1"
        self.api_key = getattr(settings, "FINNHUB_API_KEY", "").strip()
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a stock symbol"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-finnhub-api-key":
            return {
                "status": "error",
                "error": "FINNHUB_API_KEY no está configurada. Obtén una API key gratuita en https://finnhub.io/register",
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/quote",
                    params={
                        "symbol": symbol,
                        "token": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    return {
                        "status": "error",
                        "error": data.get("error", "Error desconocido"),
                        "message": "Error de API"
                    }
                
                return {
                    "status": "success",
                    "symbol": symbol,
                    "current_price": data.get("c", 0),
                    "change": data.get("d", 0),
                    "change_percent": data.get("dp", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "previous_close": data.get("pc", 0),
                    "timestamp": data.get("t", 0)
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
                    "error": f"Error inesperado: {str(e)}",
                    "message": "Error inesperado"
                }
    
    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile and fundamentals"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-finnhub-api-key":
            return {
                "status": "error",
                "error": "FINNHUB_API_KEY no está configurada. Obtén una API key gratuita en https://finnhub.io/register",
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/stock/profile2",
                    params={
                        "symbol": symbol,
                        "token": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "profile": data
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
                    "message": "Error obteniendo perfil"
                }
    
    async def get_institutional_profile(self, symbol: str) -> Dict[str, Any]:
        """Get institutional profile - ownership and holdings data"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-finnhub-api-key":
            return {
                "status": "error",
                "error": "FINNHUB_API_KEY no está configurada. Obtén una API key gratuita en https://finnhub.io/register",
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/stock/institutional-profile",
                    params={
                        "symbol": symbol,
                        "token": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "institutional_profile": data
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
                    "message": "Error obteniendo perfil institucional"
                }

