"""
Financial Modeling Prep API integration - Free tier financial data
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings


class FinancialModelingPrepAPIService:
    def __init__(self) -> None:
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.api_key = getattr(settings, "FINANCIAL_MODELING_PREP_API_KEY", "").strip()

    def _ensure_api_key(self) -> Optional[Dict[str, Any]]:
        if not self.api_key or self.api_key == "" or self.api_key == "your-fmp-api-key":
            return {
                "status": "error",
                "error": "FINANCIAL_MODELING_PREP_API_KEY no está configurada. Obtén una API key en https://site.financialmodelingprep.com/developer/docs",
                "message": "API key no configurada",
            }
        return None

    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile by stock symbol."""
        api_error = self._ensure_api_key()
        if api_error:
            return api_error

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/profile/{symbol}",
                    params={"apikey": self.api_key},
                    timeout=20.0,
                )
                response.raise_for_status()
                data = response.json()
                profile = data[0] if isinstance(data, list) and data else {}

                if not profile:
                    return {
                        "status": "error",
                        "error": "Símbolo no encontrado",
                        "symbol": symbol,
                    }

                return {
                    "status": "success",
                    "symbol": symbol,
                    "profile": profile,
                }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "message": "Error de conexión",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error inesperado",
                }

    async def get_ratios(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Get financial ratios for a company."""
        api_error = self._ensure_api_key()
        if api_error:
            return api_error

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/ratios/{symbol}",
                    params={"apikey": self.api_key, "limit": limit},
                    timeout=20.0,
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    return {
                        "status": "error",
                        "error": "Ratios no disponibles",
                        "symbol": symbol,
                    }

                return {
                    "status": "success",
                    "symbol": symbol,
                    "ratios": data,
                }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "message": "Error de conexión",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error inesperado",
                }

    async def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for symbols by company name."""
        api_error = self._ensure_api_key()
        if api_error:
            return api_error

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"query": query, "limit": limit, "apikey": self.api_key},
                    timeout=20.0,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "status": "success",
                    "query": query,
                    "results": data,
                }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "message": "Error de conexión",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "message": "Error inesperado",
                }
