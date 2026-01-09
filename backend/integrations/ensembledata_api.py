"""
EnsembleData API integration - Social Media Scraping
Documentation: https://ensembledata.com/apis/docs
"""
import httpx
from typing import Dict, Any, Optional, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EnsembleDataAPIService:
    """Service for interacting with EnsembleData API for social media data"""

    def __init__(self):
        self.base_url = "https://api.ensembledata.com/v1"
        self.api_key = getattr(settings, "ENSEMBLEDATA_API_KEY", "").strip()
        self.headers = {
            "User-Agent": "OSINT-Platform/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _check_api_key(self) -> bool:
        """Check if API key is configured"""
        if not self.api_key or self.api_key == "" or self.api_key == "your-ensembledata-api-key":
            return False
        return True

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get_error_response(self, error_message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "status": "error",
            "error": error_message,
            "message": (
                "ENSEMBLEDATA_API_KEY no está configurada. "
                "Por favor, configura una API key válida en el archivo .env. "
                "Obtén una en https://ensembledata.com/"
            ),
            "data": None,
        }

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._check_api_key():
            return self._get_error_response("API key no configurada")
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
                response = await client.get(self._build_url(path), params=params)
                response.raise_for_status()
                payload = response.json()
                return {
                    "status": "success",
                    "data": payload.get("data", payload),
                    "units_charged": payload.get("unitsCharged") or payload.get("units_charged"),
                    "raw": payload,
                }
        except httpx.HTTPStatusError as exc:
            logger.error("EnsembleData API error: %s", exc.response.text)
            return {
                "status": "error",
                "error": exc.response.text,
                "message": "EnsembleData API request failed",
                "data": None,
            }
        except Exception as exc:
            logger.error("EnsembleData API error: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
                "message": "EnsembleData API request failed",
                "data": None,
            }

    @staticmethod
    def _extract_id(payload: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
        if not payload:
            return None
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (int, str)) and str(value).isdigit():
                return int(value)
        return None

    # TikTok methods
    async def tiktok_user_info(self, username: str) -> Dict[str, Any]:
        """Get TikTok user information"""
        return await self._get("/tt/user/info", {"username": username})

    async def tiktok_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        """Get TikTok user posts"""
        return await self._get("/tt/user/posts", {"username": username, "depth": count})

    async def tiktok_hashtag_posts(self, hashtag: str, count: int = 30) -> Dict[str, Any]:
        """Get TikTok posts by hashtag"""
        return await self._get("/tt/hashtag/posts", {"name": hashtag, "cursor": 0})

    async def tiktok_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        """Get TikTok posts by keyword"""
        return await self._get(
            "/tt/keyword/search",
            {"name": keyword, "period": "7", "sorting": "0", "match_exactly": False},
        )

    async def tiktok_post_info(self, post_url: str) -> Dict[str, Any]:
        """Get TikTok post information"""
        return await self._get("/tt/post/info", {"url": post_url})

    async def tiktok_comments(self, post_url: str, count: int = 30) -> Dict[str, Any]:
        """Get TikTok post comments"""
        return await self._get("/tt/post/comments", {"aweme_id": post_url, "cursor": 0})

    # Instagram methods
    async def instagram_user_info(self, username: str) -> Dict[str, Any]:
        """Get Instagram user information"""
        return await self._get("/instagram/user/info", {"username": username})

    async def instagram_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        """Get Instagram user posts"""
        info = await self.instagram_user_info(username)
        user_id = None
        if info.get("status") == "success":
            data = info.get("data") or {}
            user_id = self._extract_id(data if isinstance(data, dict) else {}, ("user_id", "id", "pk"))
        if not user_id:
            return {
                "status": "error",
                "error": "Unable to resolve Instagram user_id from username",
                "username": username,
                "data": None,
            }
        return await self._get("/instagram/user/posts", {"user_id": user_id, "depth": count})

    async def instagram_hashtag_posts(self, hashtag: str, count: int = 30) -> Dict[str, Any]:
        """Get Instagram posts by hashtag"""
        return await self._get("/instagram/search", {"text": hashtag})

    async def instagram_post_info(self, post_url: str) -> Dict[str, Any]:
        """Get Instagram post information"""
        return await self._get("/instagram/post/details", {"code": post_url})

    async def instagram_comments(self, post_url: str, count: int = 30) -> Dict[str, Any]:
        """Get Instagram post comments"""
        return await self._get(
            "/instagram/post/comments",
            {"media_id": post_url, "cursor": "", "sorting": "recent"},
        )

    # YouTube methods
    async def youtube_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get YouTube channel information"""
        return await self._get("/youtube/channel/detailed-info", {"browseId": channel_id})

    async def youtube_channel_videos(self, channel_id: str, count: int = 30) -> Dict[str, Any]:
        """Get YouTube channel videos"""
        return await self._get("/youtube/channel/videos", {"browseId": channel_id, "depth": count})

    async def youtube_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        """Get YouTube videos by keyword"""
        return await self._get(
            "/youtube/search",
            {"keyword": keyword, "depth": count, "period": "week", "sorting": "relevance"},
        )

    async def youtube_video_info(self, video_id: str) -> Dict[str, Any]:
        """Get YouTube video information"""
        return await self._get("/youtube/channel/get-short-stats", {"id": video_id})

    async def youtube_comments(self, video_id: str, count: int = 30) -> Dict[str, Any]:
        """Get YouTube video comments"""
        return await self._get("/youtube/video/comments", {"id": video_id, "cursor": ""})

    # Threads methods
    async def threads_user_info(self, username: str) -> Dict[str, Any]:
        """Get Threads user information"""
        search = await self._get("/threads/user/search", {"name": username})
        user_id = None
        if search.get("status") == "success":
            data = search.get("data") or []
            if isinstance(data, list) and data:
                user_id = self._extract_id(data[0], ("id", "user_id"))
        if not user_id:
            return search
        return await self._get("/threads/user/info", {"id": user_id})

    async def threads_user_posts(self, username: str, count: int = 30) -> Dict[str, Any]:
        """Get Threads user posts"""
        search = await self._get("/threads/user/search", {"name": username})
        user_id = None
        if search.get("status") == "success":
            data = search.get("data") or []
            if isinstance(data, list) and data:
                user_id = self._extract_id(data[0], ("id", "user_id"))
        if not user_id:
            return search
        return await self._get("/threads/user/posts", {"id": user_id, "chunk_size": count})

    async def threads_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        """Get Threads posts by keyword"""
        return await self._get("/threads/keyword/search", {"name": keyword, "sorting": "0"})

    # Reddit methods
    async def reddit_subreddit_posts(self, subreddit: str, count: int = 25) -> Dict[str, Any]:
        """Get Reddit posts by subreddit"""
        return await self._get(
            "/reddit/subreddit/posts",
            {"name": subreddit, "sort": "hot", "period": "day"},
        )

    async def reddit_comments(self, permalink: str) -> Dict[str, Any]:
        """Get Reddit post comments"""
        return await self._get("/reddit/post/comments", {"permalink": permalink})

    # Twitter/X methods
    async def twitter_user_info(self, username: str) -> Dict[str, Any]:
        """Get Twitter user information"""
        return await self._get("/twitter/user/info", {"name": username})

    async def twitter_user_tweets(self, username: str, count: int = 20) -> Dict[str, Any]:
        """Get Twitter user tweets"""
        info = await self.twitter_user_info(username)
        user_id = None
        if info.get("status") == "success":
            data = info.get("data") or {}
            user_id = self._extract_id(data if isinstance(data, dict) else {}, ("id", "user_id"))
        if not user_id:
            return info
        return await self._get("/twitter/user/tweets", {"id": user_id})

    async def twitter_post_info(self, tweet_id: str) -> Dict[str, Any]:
        """Get Twitter tweet information"""
        return await self._get("/twitter/post/info", {"id": tweet_id})

    # Twitch methods
    async def twitch_keyword_posts(self, keyword: str, count: int = 30) -> Dict[str, Any]:
        """Get Twitch posts by keyword"""
        return await self._get("/twitch/search", {"keyword": keyword, "depth": count, "type": "videos"})

    # Snapchat methods
    async def snapchat_user_info(self, username: str) -> Dict[str, Any]:
        """Get Snapchat user information"""
        return await self._get("/snapchat/user/info", {"name": username})
