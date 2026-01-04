"""
Alpha Vantage API integration - Free stock market data
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class AlphaVantageAPIService:
    def __init__(self):
        self.base_url = "https://www.alphavantage.co/query"
        self.api_key = getattr(settings, "ALPHAVANTAGE_API_KEY", "").strip()
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for a stock symbol"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-alphavantage-api-key":
            return {
                "status": "error",
                "error": "ALPHAVANTAGE_API_KEY no está configurada. Obtén una API key gratuita en https://www.alphavantage.co/support/#api-key",
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "Error Message" in data:
                    return {
                        "status": "error",
                        "error": data.get("Error Message", "Error desconocido"),
                        "message": "Error de API"
                    }
                
                if "Note" in data:
                    return {
                        "status": "error",
                        "error": "Límite de peticiones excedido. Alpha Vantage permite 5 peticiones por minuto y 500 por día en el plan gratuito.",
                        "message": "Límite excedido"
                    }
                
                quote = data.get("Global Quote", {})
                if not quote:
                    return {
                        "status": "error",
                        "error": "Símbolo no encontrado o datos no disponibles",
                        "message": "Datos no disponibles"
                    }
                
                return {
                    "status": "success",
                    "symbol": quote.get("01. symbol", symbol),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%"),
                    "volume": int(quote.get("06. volume", 0)),
                    "high": float(quote.get("03. high", 0)),
                    "low": float(quote.get("04. low", 0)),
                    "open": float(quote.get("02. open", 0)),
                    "previous_close": float(quote.get("08. previous close", 0))
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
    
    async def search_symbol(self, keywords: str) -> Dict[str, Any]:
        """Search for stock symbols"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-alphavantage-api-key":
            return {
                "status": "error",
                "error": "ALPHAVANTAGE_API_KEY no está configurada",
                "bestMatches": []
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.base_url,
                    params={
                        "function": "SYMBOL_SEARCH",
                        "keywords": keywords,
                        "apikey": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "Error Message" in data:
                    return {
                        "status": "error",
                        "error": data.get("Error Message", "Error desconocido"),
                        "bestMatches": []
                    }
                
                return {
                    "status": "success",
                    "bestMatches": data.get("bestMatches", [])
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "bestMatches": []
                }









