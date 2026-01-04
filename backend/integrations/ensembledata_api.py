"""
EnsembleData API integration - Social media scraping
Documentation: https://ensembledata.com/apis/docs
"""
import logging
from typing import Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EnsembleDataAPIService:
    def __init__(self) -> None:
        self.base_url = "https://api.ensembledata.com"
        self.api_key = getattr(settings, "ENSEMBLEDATA_API_KEY", "").strip()
        self.headers = {
            "User-Agent": "OSINT-Platform/1.0",
        }
        if self.api_key:
            self.headers.update(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "X-API-KEY": self.api_key,
                }
            )

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _missing_key_response(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": (
                "ENSEMBLEDATA_API_KEY no está configurada. "
                "Configura una API key válida en el archivo .env para habilitar esta integración."
            ),
            "message": "Integración no disponible",
            "data": [],
        }

    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available:
            logger.warning("EnsembleData API request skipped: missing ENSEMBLEDATA_API_KEY")
            return self._missing_key_response()

        request_params = dict(params)
        request_params.setdefault("api_key", self.api_key)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/{endpoint}",
                    params=request_params,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    return data
                return {"status": "success", "data": data}
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    "EnsembleData API HTTP error %s for %s: %s",
                    status_code,
                    endpoint,
                    e,
                )
                if status_code in {401, 403}:
                    error_message = "API key inválida o no autorizada. Verifica ENSEMBLEDATA_API_KEY."
                elif status_code == 429:
                    error_message = "Límite de peticiones excedido en EnsembleData."
                else:
                    error_message = f"Error HTTP {status_code}: {e}"
                return {
                    "status": "error",
                    "error": error_message,
                    "message": "Error en la petición",
                    "data": [],
                }
            except httpx.HTTPError as e:
                logger.warning("EnsembleData API connection error for %s: %s", endpoint, e)
                return {
                    "status": "error",
                    "error": f"Error de conexión: {e}",
                    "message": "Error de conexión",
                    "data": [],
                }
            except Exception as e:
                logger.exception("Unexpected EnsembleData API error for %s", endpoint)
                return {
                    "status": "error",
                    "error": f"Error inesperado: {e}",
                    "message": "Error inesperado",
                    "data": [],
                }

    # TikTok
    async def tiktok_user_info(self, username: str) -> Dict[str, Any]:
        return await self._request("tiktok/user/info", {"username": username})

    async def tiktok_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "tiktok/user/posts",
            {"username": username, "count": count},
        )

    async def tiktok_hashtag_posts(self, hashtag: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "tiktok/hashtag/posts",
            {"hashtag": hashtag, "count": count},
        )

    async def tiktok_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "tiktok/keyword/posts",
            {"keyword": keyword, "count": count},
        )

    async def tiktok_post_info(self, post_url: str) -> Dict[str, Any]:
        return await self._request("tiktok/post/info", {"post_url": post_url})

    async def tiktok_comments(self, post_url: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "tiktok/post/comments",
            {"post_url": post_url, "count": count},
        )

    # Instagram
    async def instagram_user_info(self, username: str) -> Dict[str, Any]:
        return await self._request("instagram/user/info", {"username": username})

    async def instagram_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "instagram/user/posts",
            {"username": username, "count": count},
        )

    async def instagram_hashtag_posts(self, hashtag: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "instagram/hashtag/posts",
            {"hashtag": hashtag, "count": count},
        )

    async def instagram_post_info(self, post_url: str) -> Dict[str, Any]:
        return await self._request("instagram/post/info", {"post_url": post_url})

    async def instagram_comments(self, post_url: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "instagram/post/comments",
            {"post_url": post_url, "count": count},
        )

    # YouTube
    async def youtube_channel_info(self, channel_id: str) -> Dict[str, Any]:
        return await self._request("youtube/channel/info", {"channel_id": channel_id})

    async def youtube_channel_videos(self, channel_id: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "youtube/channel/videos",
            {"channel_id": channel_id, "count": count},
        )

    async def youtube_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "youtube/keyword/posts",
            {"keyword": keyword, "count": count},
        )

    async def youtube_video_info(self, video_id: str) -> Dict[str, Any]:
        return await self._request("youtube/video/info", {"video_id": video_id})

    async def youtube_comments(self, video_id: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "youtube/video/comments",
            {"video_id": video_id, "count": count},
        )

    # Threads
    async def threads_user_info(self, username: str) -> Dict[str, Any]:
        return await self._request("threads/user/info", {"username": username})

    async def threads_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "threads/user/posts",
            {"username": username, "count": count},
        )

    async def threads_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "threads/keyword/posts",
            {"keyword": keyword, "count": count},
        )

    # Reddit (additional)
    async def reddit_subreddit_posts(self, subreddit: str, count: int = 25) -> Dict[str, Any]:
        return await self._request(
            "reddit/subreddit/posts",
            {"subreddit": subreddit, "count": count},
        )

    async def reddit_comments(self, post_url: str, count: int = 25) -> Dict[str, Any]:
        return await self._request(
            "reddit/post/comments",
            {"post_url": post_url, "count": count},
        )

    # Twitter/X
    async def twitter_user_info(self, username: str) -> Dict[str, Any]:
        return await self._request("twitter/user/info", {"username": username})

    async def twitter_user_tweets(self, username: str, count: int = 20) -> Dict[str, Any]:
        return await self._request(
            "twitter/user/tweets",
            {"username": username, "count": count},
        )

    async def twitter_post_info(self, tweet_url: str) -> Dict[str, Any]:
        return await self._request("twitter/post/info", {"tweet_url": tweet_url})

    # Twitch
    async def twitch_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        return await self._request(
            "twitch/keyword/posts",
            {"keyword": keyword, "count": count},
        )

    # Snapchat
    async def snapchat_user_info(self, username: str) -> Dict[str, Any]:
        return await self._request("snapchat/user/info", {"username": username})
