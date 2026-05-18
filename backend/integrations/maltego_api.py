"""
Maltego Transform API integration
"""
import httpx
from typing import Dict, Any, Optional
from app.config import settings


class MaltegoAPIService:
    def __init__(self) -> None:
        self.base_url = getattr(settings, "MALTEGO_API_URL", "").strip()
        self.api_key = getattr(settings, "MALTEGO_API_KEY", "").strip()

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_url(self, endpoint: Optional[str], transform: str) -> Optional[str]:
        if endpoint:
            if endpoint.startswith("http"):
                return endpoint
            if self.base_url:
                return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            return None
        if not self.base_url:
            return None
        return f"{self.base_url.rstrip('/')}/transform/{transform}"

    async def execute_transform(
        self,
        transform: str,
        entity_type: str,
        value: str,
        params: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a Maltego transform using a configured Transform Server endpoint."""
        url = self._build_url(endpoint, transform)
        if not url:
            return {
                "status": "error",
                "error": "MALTEGO_API_URL no está configurada.",
                "message": "API base URL no configurada",
            }

        payload = {
            "transform": transform,
            "entity_type": entity_type,
            "value": value,
            "params": params or {},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._build_headers(),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "status": "success",
                    "transform": transform,
                    "entity_type": entity_type,
                    "value": value,
                    "data": data,
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
