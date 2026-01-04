"""
Currency Exchange API integration - Free currency conversion
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class CurrencyAPIService:
    def __init__(self):
        # ExchangeRate-API (free tier: 1,500 requests/month)
        self.exchangerate_url = "https://v6.exchangerate-api.com/v6"
        self.exchangerate_key = getattr(settings, "EXCHANGERATE_API_KEY", "").strip()
        
        # Fixer.io (free tier: 100 requests/month)
        self.fixer_url = "https://api.fixer.io"
        self.fixer_key = getattr(settings, "FIXER_API_KEY", "").strip()
    
    async def get_rates(
        self,
        base: str = "USD",
        provider: str = "exchangerate"  # exchangerate or fixer
    ) -> Dict[str, Any]:
        """Get currency exchange rates"""
        if provider == "fixer":
            return await self._get_fixer_rates(base)
        else:
            return await self._get_exchangerate_rates(base)
    
    async def _get_exchangerate_rates(self, base: str) -> Dict[str, Any]:
        """Get rates from ExchangeRate-API"""
        if not self.exchangerate_key or self.exchangerate_key == "" or self.exchangerate_key == "your-exchangerate-api-key":
            return {
                "status": "error",
                "error": "EXCHANGERATE_API_KEY no está configurada. Obtén una API key gratuita en https://www.exchangerate-api.com/",
                "message": "API key no configurada",
                "info": "Plan gratuito: 1,500 requests/mes"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.exchangerate_url}/{self.exchangerate_key}/latest/{base}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("result") == "error":
                    return {
                        "status": "error",
                        "error": data.get("error-type", "Unknown error"),
                        "message": "Error de API"
                    }
                
                return {
                    "status": "success",
                    "base": data.get("base_code", base),
                    "rates": data.get("conversion_rates", {}),
                    "last_update": data.get("time_last_update_utc", "")
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
                    "message": "Error inesperado"
                }
    
    async def _get_fixer_rates(self, base: str) -> Dict[str, Any]:
        """Get rates from Fixer.io"""
        if not self.fixer_key or self.fixer_key == "" or self.fixer_key == "your-fixer-api-key":
            return {
                "status": "error",
                "error": "FIXER_API_KEY no está configurada. Obtén una API key gratuita en https://fixer.io/",
                "message": "API key no configurada",
                "info": "Plan gratuito: 100 requests/mes"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.fixer_url}/latest",
                    params={
                        "access_key": self.fixer_key,
                        "base": base
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("success", True):
                    return {
                        "status": "error",
                        "error": data.get("error", {}).get("info", "Unknown error"),
                        "message": "Error de API"
                    }
                
                return {
                    "status": "success",
                    "base": data.get("base", base),
                    "rates": data.get("rates", {}),
                    "date": data.get("date", "")
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error obteniendo tasas"
                }
    
    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        provider: str = "exchangerate"
    ) -> Dict[str, Any]:
        """Convert currency amount"""
        rates_result = await self.get_rates(from_currency, provider)
        
        if rates_result.get("status") != "success":
            return rates_result
        
        rates = rates_result.get("rates", {})
        if to_currency not in rates:
            return {
                "status": "error",
                "error": f"Currency {to_currency} not found in rates"
            }
        
        converted = amount * rates[to_currency]
        
        return {
            "status": "success",
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
            "rate": rates[to_currency],
            "converted": converted
        }









