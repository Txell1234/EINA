"""
OSINT Service - Integration with OSINT tools
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from models.osint import OSINTQuery, OSINTResult, OSINTSource
from integrations.sherlock_wrapper import SherlockWrapper
from integrations.reconng_wrapper import ReconNGWrapper
from integrations.news_api import NewsAPIService
from integrations.github_api import GitHubAPIService
from integrations.reddit_api import RedditAPIService
from integrations.theharvester_wrapper import TheHarvesterWrapper
from integrations.shodan_api import ShodanAPIService
from integrations.wayback_api import WaybackAPIService
from integrations.dns_whois import DNSWhoisService
from integrations.ensembledata_api import EnsembleDataAPIService

class OSINTService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sherlock = SherlockWrapper()
        self.reconng = ReconNGWrapper()
        self.news = NewsAPIService()
        self.github = GitHubAPIService()
        self.reddit = RedditAPIService()
        self.theharvester = TheHarvesterWrapper()
        self.shodan = ShodanAPIService()
        self.wayback = WaybackAPIService()
        self.dns_whois = DNSWhoisService()
        self.ensembledata = EnsembleDataAPIService()
    
    async def execute_query(
        self,
        query_type: str,
        query_params: Dict[str, Any],
        case_id: int = None
    ) -> Dict[str, Any]:
        """Execute OSINT query"""
        # Create query record
        query = OSINTQuery(
            query_type=query_type,
            query_params=query_params,
            case_id=case_id,
            status="running"
        )
        self.db.add(query)
        await self.db.commit()
        await self.db.refresh(query)
        
        try:
            # Execute based on type
            if query_type == "sherlock":
                result_data = await self.sherlock.search(
                    username=query_params.get("username", "")
                )
            elif query_type == "recon-ng":
                result_data = await self.reconng.execute_module(
                    module=query_params.get("module", "domain"),
                    params=query_params
                )
            elif query_type == "google_news":
                result_data = await self.news.search(
                    query=query_params.get("query", ""),
                    language=query_params.get("language", "es")
                )
            elif query_type == "reddit":
                result_data = await self.reddit.search(
                    query=query_params.get("query", ""),
                    subreddit=query_params.get("subreddit")
                )
            elif query_type == "github":
                result_data = await self.github.search(
                    query=query_params.get("query", ""),
                    type=query_params.get("type", "repositories")
                )
            elif query_type == "theharvester":
                result_data = await self.theharvester.search(
                    domain=query_params.get("domain", ""),
                    sources=query_params.get("sources"),
                    limit=query_params.get("limit", 500)
                )
            elif query_type == "shodan":
                result_data = await self.shodan.search(
                    query=query_params.get("query", ""),
                    facets=query_params.get("facets"),
                    page=query_params.get("page", 1)
                )
            elif query_type == "shodan_host":
                result_data = await self.shodan.host_info(
                    ip=query_params.get("ip", "")
                )
            elif query_type == "wayback":
                result_data = await self.wayback.get_snapshots(
                    url=query_params.get("url", ""),
                    limit=query_params.get("limit", 10),
                    from_date=query_params.get("from_date"),
                    to_date=query_params.get("to_date")
                )
            elif query_type == "dns":
                result_data = await self.dns_whois.dns_lookup(
                    domain=query_params.get("domain", ""),
                    record_types=query_params.get("record_types")
                )
            elif query_type == "whois":
                result_data = await self.dns_whois.whois_lookup(
                    domain=query_params.get("domain", "")
                )
            elif query_type == "reverse_dns":
                result_data = await self.dns_whois.reverse_dns(
                    ip=query_params.get("ip", "")
                )
            elif query_type == "ip_geolocation":
                from integrations.ipstack_api import IPStackAPIService
                ipstack = IPStackAPIService()
                result_data = await ipstack.get_ip_info(
                    ip_address=query_params.get("ip", ""),
                    hostname=query_params.get("hostname", True),
                    security=query_params.get("security", True)
                )
            # EnsembleData - TikTok
            elif query_type == "ensembledata_tiktok_user_info":
                result_data = await self.ensembledata.tiktok_user_info(
                    username=query_params.get("username", "")
                )
            elif query_type == "ensembledata_tiktok_user_posts":
                result_data = await self.ensembledata.tiktok_user_posts(
                    username=query_params.get("username", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_tiktok_hashtag_posts":
                result_data = await self.ensembledata.tiktok_hashtag_posts(
                    hashtag=query_params.get("hashtag", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_tiktok_keyword_posts":
                result_data = await self.ensembledata.tiktok_keyword_posts(
                    keyword=query_params.get("keyword", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_tiktok_post_info":
                result_data = await self.ensembledata.tiktok_post_info(
                    post_url=query_params.get("post_url", "")
                )
            elif query_type == "ensembledata_tiktok_comments":
                result_data = await self.ensembledata.tiktok_comments(
                    post_url=query_params.get("post_url", ""),
                    count=query_params.get("count", 30)
                )
            # EnsembleData - Instagram
            elif query_type == "ensembledata_instagram_user_info":
                result_data = await self.ensembledata.instagram_user_info(
                    username=query_params.get("username", "")
                )
            elif query_type == "ensembledata_instagram_user_posts":
                result_data = await self.ensembledata.instagram_user_posts(
                    username=query_params.get("username", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_instagram_hashtag_posts":
                result_data = await self.ensembledata.instagram_hashtag_posts(
                    hashtag=query_params.get("hashtag", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_instagram_post_info":
                result_data = await self.ensembledata.instagram_post_info(
                    post_url=query_params.get("post_url", "")
                )
            elif query_type == "ensembledata_instagram_comments":
                result_data = await self.ensembledata.instagram_comments(
                    post_url=query_params.get("post_url", ""),
                    count=query_params.get("count", 30)
                )
            # EnsembleData - YouTube
            elif query_type == "ensembledata_youtube_channel_info":
                result_data = await self.ensembledata.youtube_channel_info(
                    channel_id=query_params.get("channel_id", "")
                )
            elif query_type == "ensembledata_youtube_channel_videos":
                result_data = await self.ensembledata.youtube_channel_videos(
                    channel_id=query_params.get("channel_id", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_youtube_keyword_posts":
                result_data = await self.ensembledata.youtube_keyword_posts(
                    keyword=query_params.get("keyword", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_youtube_video_info":
                result_data = await self.ensembledata.youtube_video_info(
                    video_id=query_params.get("video_id", "")
                )
            elif query_type == "ensembledata_youtube_comments":
                result_data = await self.ensembledata.youtube_comments(
                    video_id=query_params.get("video_id", ""),
                    count=query_params.get("count", 30)
                )
            # EnsembleData - Threads
            elif query_type == "ensembledata_threads_user_info":
                result_data = await self.ensembledata.threads_user_info(
                    username=query_params.get("username", "")
                )
            elif query_type == "ensembledata_threads_user_posts":
                result_data = await self.ensembledata.threads_user_posts(
                    username=query_params.get("username", ""),
                    count=query_params.get("count", 30)
                )
            elif query_type == "ensembledata_threads_keyword_posts":
                result_data = await self.ensembledata.threads_keyword_posts(
                    keyword=query_params.get("keyword", ""),
                    count=query_params.get("count", 30)
                )
            # EnsembleData - Reddit (adicional)
            elif query_type == "ensembledata_reddit_subreddit_posts":
                result_data = await self.ensembledata.reddit_subreddit_posts(
                    subreddit=query_params.get("subreddit", ""),
                    count=query_params.get("count", 25)
                )
            elif query_type == "ensembledata_reddit_comments":
                result_data = await self.ensembledata.reddit_comments(
                    post_url=query_params.get("post_url", ""),
                    count=query_params.get("count", 25)
                )
            # EnsembleData - Twitter/X
            elif query_type == "ensembledata_twitter_user_info":
                result_data = await self.ensembledata.twitter_user_info(
                    username=query_params.get("username", "")
                )
            elif query_type == "ensembledata_twitter_user_tweets":
                result_data = await self.ensembledata.twitter_user_tweets(
                    username=query_params.get("username", ""),
                    count=query_params.get("count", 20)
                )
            elif query_type == "ensembledata_twitter_post_info":
                result_data = await self.ensembledata.twitter_post_info(
                    tweet_url=query_params.get("tweet_url", "")
                )
            # EnsembleData - Twitch
            elif query_type == "ensembledata_twitch_keyword_posts":
                result_data = await self.ensembledata.twitch_keyword_posts(
                    keyword=query_params.get("keyword", ""),
                    count=query_params.get("count", 30)
                )
            # EnsembleData - Snapchat
            elif query_type == "ensembledata_snapchat_user_info":
                result_data = await self.ensembledata.snapchat_user_info(
                    username=query_params.get("username", "")
                )
            else:
                result_data = {"error": f"Unknown query type: {query_type}"}
            
            # Determine result status
            has_error = (
                isinstance(result_data, dict)
                and (
                    result_data.get("status") == "error"
                    or result_data.get("error") is not None
                )
            )
            result_status = "error" if has_error else "completed"

            # Create result record
            result = OSINTResult(
                query_id=query.id,
                data=result_data,
                status=result_status,
                error_message=result_data.get("error") if has_error else None
            )
            self.db.add(result)
            await self.db.flush()  # Flush to get result.id
            
            # Update query status
            # Si hay un error en result_data, marcar como completed pero con error
            query.status = "completed"
            
            await self.db.commit()
            
            # IMPORTANT: Classify OSINT result through AI automatically
            # This ensures all data is classified before visualization
            if case_id and not has_error:
                try:
                    from services.ai_classification_service import AIClassificationService
                    classification_service = AIClassificationService(self.db)
                    await classification_service.classify_osint_result(result, case_id)
                    await self.db.commit()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error auto-classifying OSINT result {result.id}: {e}")
                    # Don't fail the OSINT collection if classification fails
            
            return {
                "query_id": query.id,
                "result_id": result.id,
                "data": result_data,
                "status": result_status,
                "error": result_data.get("error") if has_error else None
            }
            
        except Exception as e:
            query.status = "failed"
            await self.db.commit()
            return {
                "query_id": query.id,
                "error": str(e),
                "status": "failed",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "message": "Error ejecutando consulta OSINT"
                }
            }
