"""Map OSINT query_type ensembledata_* to EnsembleData API calls."""
from __future__ import annotations

from typing import Any

from integrations.ensembledata_api import EnsembleDataAPIService


def _count(params: dict[str, Any], default: int = 30) -> int:
    raw = params.get("count") or params.get("max_results") or params.get("depth") or default
    try:
        return max(1, min(int(raw), 100))
    except (TypeError, ValueError):
        return default


async def execute_ensembledata_query(
    query_type: str,
    query_params: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch ensembledata_* query types to the API service."""
    svc = EnsembleDataAPIService()
    p = query_params or {}

    username = str(p.get("username") or p.get("user") or "").strip()
    keyword = str(p.get("keyword") or p.get("query") or "").strip()
    hashtag = str(p.get("hashtag") or p.get("tag") or keyword).strip().lstrip("#")
    channel_id = str(p.get("channel_id") or p.get("browseId") or "").strip()
    subreddit = str(p.get("subreddit") or p.get("name") or "").strip().lstrip("r/")
    post_url = str(p.get("url") or p.get("post_url") or "").strip()
    tweet_id = str(p.get("tweet_id") or p.get("id") or "").strip()
    count = _count(p)

    handlers: dict[str, Any] = {
        "ensembledata_tiktok_user_info": lambda: svc.tiktok_user_info(username),
        "ensembledata_tiktok_user_posts": lambda: svc.tiktok_user_posts(username, count),
        "ensembledata_tiktok_hashtag_posts": lambda: svc.tiktok_hashtag_posts(hashtag, count),
        "ensembledata_tiktok_keyword_posts": lambda: svc.tiktok_keyword_posts(keyword, count),
        "ensembledata_tiktok_post_info": lambda: svc.tiktok_post_info(post_url),
        "ensembledata_tiktok_comments": lambda: svc.tiktok_comments(post_url, count),
        "ensembledata_instagram_user_info": lambda: svc.instagram_user_info(username),
        "ensembledata_instagram_user_posts": lambda: svc.instagram_user_posts(username, count),
        "ensembledata_instagram_hashtag_posts": lambda: svc.instagram_hashtag_posts(hashtag, count),
        "ensembledata_instagram_post_info": lambda: svc.instagram_post_info(post_url),
        "ensembledata_instagram_comments": lambda: svc.instagram_comments(post_url, count),
        "ensembledata_youtube_channel_info": lambda: svc.youtube_channel_info(channel_id),
        "ensembledata_youtube_channel_videos": lambda: svc.youtube_channel_videos(channel_id, count),
        "ensembledata_youtube_keyword_posts": lambda: svc.youtube_keyword_posts(keyword, count),
        "ensembledata_youtube_video_info": lambda: svc.youtube_video_info(
            str(p.get("video_id") or tweet_id or "").strip()
        ),
        "ensembledata_youtube_comments": lambda: svc.youtube_comments(
            str(p.get("video_id") or "").strip(), count
        ),
        "ensembledata_threads_user_info": lambda: svc.threads_user_info(username),
        "ensembledata_threads_user_posts": lambda: svc.threads_user_posts(username, count),
        "ensembledata_threads_keyword_posts": lambda: svc.threads_keyword_posts(keyword, count),
        "ensembledata_reddit_subreddit_posts": lambda: svc.reddit_subreddit_posts(subreddit, count),
        "ensembledata_reddit_comments": lambda: svc.reddit_comments(
            str(p.get("permalink") or post_url or "").strip()
        ),
        "ensembledata_twitter_user_info": lambda: svc.twitter_user_info(username),
        "ensembledata_twitter_user_tweets": lambda: svc.twitter_user_tweets(username, count),
        "ensembledata_twitter_post_info": lambda: svc.twitter_post_info(tweet_id),
        "ensembledata_twitch_keyword_posts": lambda: svc.twitch_keyword_posts(keyword, count),
        "ensembledata_snapchat_user_info": lambda: svc.snapchat_user_info(username),
    }

    handler = handlers.get(query_type)
    if not handler:
        return {
            "status": "error",
            "error": f"Unknown EnsembleData query type: {query_type}",
            "query_type": query_type,
        }

    result = await handler()
    if isinstance(result, dict):
        result.setdefault("query_type", query_type)
        result.setdefault("platform", query_type.replace("ensembledata_", "").split("_")[0])
    return result
