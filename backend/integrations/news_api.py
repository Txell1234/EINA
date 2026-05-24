"""
Google News integration — NewsAPI.org when configured, Google News RSS fallback otherwise.
"""
import logging
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.config import settings
from services.osint_data_utils import extract_search_keywords, normalize_search_query

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _news_api_configured() -> bool:
    key = getattr(settings, "NEWS_API_KEY", "").strip()
    return bool(key and key != "your-news-api-key")


class NewsAPIService:
    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
        self.api_key = getattr(settings, "NEWS_API_KEY", "").strip()

    async def search(
        self,
        query: str,
        language: str = "es",
        sort_by: str = "publishedAt",
    ) -> dict[str, Any]:
        query = extract_search_keywords(query) if len(query) > 100 else normalize_search_query(query)

        if not _news_api_configured():
            return await self._search_google_news_rss(query, language)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/everything",
                    params={
                        "q": query,
                        "language": language,
                        "sortBy": sort_by,
                        "apiKey": self.api_key,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                payload.setdefault("status", "ok")
                payload["provider"] = "newsapi"
                return payload
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 429):
                    logger.warning("NewsAPI %s — fallback a Google News RSS", e.response.status_code)
                    return await self._search_google_news_rss(query, language)
                return {
                    "status": "error",
                    "error": f"Error HTTP {e.response.status_code}: {e}",
                    "articles": [],
                    "message": "Error en la petició",
                }
            except httpx.HTTPError as e:
                logger.warning("NewsAPI connexió fallida — fallback RSS: %s", e)
                return await self._search_google_news_rss(query, language)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error inesperat: {e}",
                    "articles": [],
                    "message": "Error inesperat",
                }

    async def _search_google_news_rss(self, query: str, language: str = "es") -> dict[str, Any]:
        """Free fallback via Google News RSS (no API key)."""
        try:
            import feedparser
        except ImportError:
            return {
                "status": "error",
                "error": "feedparser no instal·lat. Executa: pip install feedparser",
                "articles": [],
                "message": "Dependència absent",
            }

        lang = (language or "en")[:2].lower()
        hl_map = {"es": "es-419", "ca": "es-419", "en": "en-US", "fr": "fr-FR", "de": "de-DE"}
        hl = hl_map.get(lang, f"{lang}-{lang.upper()}")
        url = f"{GOOGLE_NEWS_RSS}?q={quote_plus(query)}&hl={hl}&gl=US&ceid=US:{lang}"

        try:
            async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "EINA-OSINT/1.0"})
                resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            articles = []
            for entry in feed.entries[:30]:
                articles.append(
                    {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "link", ""),
                        "publishedAt": getattr(entry, "published", ""),
                        "description": getattr(entry, "summary", "")[:500],
                        "source": {"name": getattr(entry, "source", {}).get("title", "Google News")},
                    }
                )
            return {
                "status": "ok",
                "totalResults": len(articles),
                "articles": articles,
                "provider": "google_news_rss",
                "message": "Recollida via Google News RSS (NEWS_API_KEY no configurada)",
            }
        except Exception as e:
            logger.error("Google News RSS error: %s", e)
            return {
                "status": "error",
                "error": f"No s'ha pogut obtenir Google News RSS: {e}",
                "articles": [],
                "message": str(e),
            }
