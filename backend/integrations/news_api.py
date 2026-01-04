"""
Google News API integration
"""
import httpx
from typing import Dict, Any, List
from app.config import settings

class NewsAPIService:
    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
        self.api_key = getattr(settings, "NEWS_API_KEY", "").strip()
    
    async def search(
        self,
        query: str,
        language: str = "es",
        sort_by: str = "publishedAt"
    ) -> Dict[str, Any]:
        """Search news articles"""
        # Validar API key antes de hacer la petición
        if not self.api_key or self.api_key == "" or self.api_key == "your-news-api-key":
            return {
                "status": "error",
                "error": "NEWS_API_KEY no está configurada. Por favor, configura una API key válida en el archivo .env. Obtén una en https://newsapi.org/register",
                "articles": [],
                "message": "API key no configurada"
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/everything",
                    params={
                        "q": query,
                        "language": language,
                        "sortBy": sort_by,
                        "apiKey": self.api_key
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Manejar errores HTTP específicos
                if e.response.status_code == 401:
                    return {
                        "status": "error",
                        "error": "API key inválida o no autorizada. Verifica tu NEWS_API_KEY en el archivo .env",
                        "articles": [],
                        "message": "Error de autenticación"
                    }
                elif e.response.status_code == 429:
                    return {
                        "status": "error",
                        "error": "Límite de peticiones excedido. Intenta más tarde o actualiza tu plan de NewsAPI",
                        "articles": [],
                        "message": "Límite excedido"
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Error HTTP {e.response.status_code}: {str(e)}",
                        "articles": [],
                        "message": "Error en la petición"
                    }
            except httpx.HTTPError as e:
                return {
                    "status": "error",
                    "error": f"Error de conexión: {str(e)}",
                    "articles": [],
                    "message": "Error de conexión"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error inesperado: {str(e)}",
                    "articles": [],
                    "message": "Error inesperado"
                }

