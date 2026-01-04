"""
CoinGecko API integration - Free cryptocurrency data
No API key required for basic tier
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class CoinGeckoAPIService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = getattr(settings, "COINGECKO_API_KEY", "").strip()
        # Note: CoinGecko free tier doesn't require API key, but has rate limits
        # With API key: 50 calls/minute, without: 10-50 calls/minute
    
    async def get_price(
        self,
        coin_id: str,
        vs_currencies: str = "usd"
    ) -> Dict[str, Any]:
        """Get cryptocurrency price"""
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "ids": coin_id,
                    "vs_currencies": vs_currencies,
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true"
                }
                
                if self.api_key and self.api_key != "" and self.api_key != "your-coingecko-api-key":
                    params["x_cg_demo_api_key"] = self.api_key
                
                response = await client.get(
                    f"{self.base_url}/simple/price",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if coin_id not in data:
                    return {
                        "status": "error",
                        "error": f"Cryptocurrency {coin_id} not found",
                        "coin_id": coin_id
                    }
                
                coin_data = data[coin_id]
                return {
                    "status": "success",
                    "coin_id": coin_id,
                    "price": coin_data.get(vs_currencies, 0),
                    "market_cap": coin_data.get(f"{vs_currencies}_market_cap", 0),
                    "volume_24h": coin_data.get(f"{vs_currencies}_24h_vol", 0),
                    "change_24h": coin_data.get(f"{vs_currencies}_24h_change", 0)
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    return {
                        "status": "error",
                        "error": "Rate limit exceeded. CoinGecko free tier: 10-50 calls/minute. Consider adding COINGECKO_API_KEY for higher limits.",
                        "message": "Límite excedido"
                    }
                return {
                    "status": "error",
                    "error": f"HTTP error: {e.response.status_code}",
                    "message": "Error de API"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error inesperado"
                }
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Search for cryptocurrencies"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"query": query},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "coins": data.get("coins", [])[:10],  # Limit to 10 results
                    "exchanges": data.get("exchanges", [])[:10]
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "coins": []
                }
    
    async def get_trending(self) -> Dict[str, Any]:
        """Get trending cryptocurrencies"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/trending",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "status": "success",
                    "trending": data.get("coins", [])
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "trending": []
                }

