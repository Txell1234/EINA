"""
OSINT Service - Integration with OSINT tools
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Callable, Awaitable
from datetime import datetime
from models.osint import OSINTQuery, OSINTResult, OSINTSource, QueryStatus
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
from integrations.alphavantage_api import AlphaVantageAPIService
from integrations.finnhub_api import FinnhubAPIService
from integrations.currency_api import CurrencyAPIService
from integrations.crypto_api import CoinGeckoAPIService
from integrations.country_api import CountryAPIService
from integrations.nominatim_api import NominatimAPIService
from integrations.financial_modeling_prep_api import FinancialModelingPrepAPIService
from integrations.maltego_api import MaltegoAPIService
from services.event_bus_service import EventBusService

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
        self.alphavantage = AlphaVantageAPIService()
        self.finnhub = FinnhubAPIService()
        self.currency = CurrencyAPIService()
        self.crypto = CoinGeckoAPIService()
        self.country = CountryAPIService()
        self.nominatim = NominatimAPIService()
        self.fmp = FinancialModelingPrepAPIService()
        self.maltego = MaltegoAPIService()
        self.event_bus = EventBusService()
        self._query_handlers = self._build_query_handlers()
        self._register_event_rules()

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
            status=QueryStatus.RUNNING
        )
        self.db.add(query)
        await self.db.commit()
        await self.db.refresh(query)
        
        try:
            event = {
                "source": "osint",
                "detail_type": "query.execute",
                "detail": {
                    "query_type": query_type,
                    "params": query_params,
                    "case_id": case_id,
                },
            }
            results = await self.event_bus.publish(event)
            if results and isinstance(results[0], Exception):
                raise results[0]
            result_data = results[0] if results else {
                "status": "error",
                "error": f"Unknown query type: {query_type}",
            }
            
            # Create result record
            result = OSINTResult(
                query_id=query.id,
                data=result_data,
                status="completed"
            )
            self.db.add(result)
            await self.db.flush()  # Flush to get result.id
            
            # Update query status
            # Si hay un error en result_data, marcar como completed pero con error
            if isinstance(result_data, dict) and result_data.get("status") == "error":
                query.status = QueryStatus.COMPLETED  # Completado pero con error
            else:
                query.status = QueryStatus.COMPLETED
            query.completed_at = datetime.utcnow()
            
            await self.db.commit()
            
            await self.event_bus.publish(
                {
                    "source": "osint",
                    "detail_type": "result.created",
                    "detail": {
                        "case_id": case_id,
                        "result_id": result.id,
                    },
                }
            )
            
            return {
                "query_id": query.id,
                "result_id": result.id,
                "data": result_data,
                "status": "completed",
                "error": result_data.get("error") if isinstance(result_data, dict) and result_data.get("status") == "error" else None
            }
            
        except Exception as e:
            query.status = QueryStatus.FAILED
            query.completed_at = datetime.utcnow()
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

    def _register_event_rules(self) -> None:
        self.event_bus.register_rule(
            name="osint-query-execute",
            handler=self._handle_query_event,
            sources=["osint"],
            detail_types=["query.execute"],
        )
        self.event_bus.register_rule(
            name="osint-result-classification",
            handler=self._handle_result_created,
            sources=["osint"],
            detail_types=["result.created"],
        )

    def _build_query_handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]]:
        return {
            "sherlock": lambda params: self.sherlock.search(
                username=params.get("username", "")
            ),
            "recon-ng": lambda params: self.reconng.execute_module(
                module=params.get("module", "domain"),
                params=params,
            ),
            "google_news": lambda params: self.news.search(
                query=params.get("query", ""),
                language=params.get("language", "es"),
            ),
            "reddit": lambda params: self.reddit.search(
                query=params.get("query", ""),
                subreddit=params.get("subreddit"),
            ),
            "github": lambda params: self.github.search(
                query=params.get("query", ""),
                type=params.get("type", "repositories"),
            ),
            "theharvester": lambda params: self.theharvester.search(
                domain=params.get("domain", ""),
                sources=params.get("sources"),
                limit=params.get("limit", 500),
            ),
            "shodan": lambda params: self.shodan.search(
                query=params.get("query", ""),
                facets=params.get("facets"),
                page=params.get("page", 1),
            ),
            "shodan_host": lambda params: self.shodan.host_info(
                ip=params.get("ip", ""),
            ),
            "wayback": lambda params: self.wayback.get_snapshots(
                url=params.get("url", ""),
                limit=params.get("limit", 10),
                from_date=params.get("from_date"),
                to_date=params.get("to_date"),
            ),
            "dns": lambda params: self.dns_whois.dns_lookup(
                domain=params.get("domain", ""),
                record_types=params.get("record_types"),
            ),
            "whois": lambda params: self.dns_whois.whois_lookup(
                domain=params.get("domain", ""),
            ),
            "reverse_dns": lambda params: self.dns_whois.reverse_dns(
                ip=params.get("ip", ""),
            ),
            "ip_geolocation": self._handle_ip_geolocation,
            "nominatim_geocode": lambda params: self.nominatim.geocode(
                query=params.get("query", ""),
                limit=params.get("limit", 1),
            ),
            "nominatim_reverse": lambda params: self.nominatim.reverse_geocode(
                latitude=params.get("latitude", 0),
                longitude=params.get("longitude", 0),
            ),
            "country_info": lambda params: self.country.get_country(
                country_name=params.get("country_name", ""),
            ),
            "country_by_code": lambda params: self.country.get_country_by_code(
                code=params.get("code", ""),
            ),
            "country_search": lambda params: self.country.search_countries(
                query=params.get("query", ""),
            ),
            "currency_rates": lambda params: self.currency.get_rates(
                base=params.get("base", "USD"),
                provider=params.get("provider", "exchangerate"),
            ),
            "currency_convert": lambda params: self.currency.convert(
                amount=params.get("amount", 0),
                from_currency=params.get("from_currency", "USD"),
                to_currency=params.get("to_currency", "EUR"),
                provider=params.get("provider", "exchangerate"),
            ),
            "coingecko_price": lambda params: self.crypto.get_price(
                coin_id=params.get("coin_id", ""),
                vs_currencies=params.get("vs_currencies", "usd"),
            ),
            "coingecko_search": lambda params: self.crypto.search(
                query=params.get("query", ""),
            ),
            "coingecko_trending": lambda params: self.crypto.get_trending(),
            "alphavantage_quote": lambda params: self.alphavantage.get_quote(
                symbol=params.get("symbol", ""),
            ),
            "alphavantage_search": lambda params: self.alphavantage.search_symbol(
                keywords=params.get("keywords", ""),
            ),
            "finnhub_quote": lambda params: self.finnhub.get_quote(
                symbol=params.get("symbol", ""),
            ),
            "finnhub_profile": lambda params: self.finnhub.get_company_profile(
                symbol=params.get("symbol", ""),
            ),
            "finnhub_institutional_profile": lambda params: self.finnhub.get_institutional_profile(
                symbol=params.get("symbol", ""),
            ),
            "fmp_profile": lambda params: self.fmp.get_company_profile(
                symbol=params.get("symbol", ""),
            ),
            "fmp_ratios": lambda params: self.fmp.get_ratios(
                symbol=params.get("symbol", ""),
                limit=params.get("limit", 10),
            ),
            "fmp_search": lambda params: self.fmp.search(
                query=params.get("query", ""),
                limit=params.get("limit", 10),
            ),
            "maltego_transform": lambda params: self.maltego.execute_transform(
                transform=params.get("transform", ""),
                entity_type=params.get("entity_type", ""),
                value=params.get("value", ""),
                params=params.get("params"),
                endpoint=params.get("endpoint"),
            ),
            # EnsembleData - TikTok
            "ensembledata_tiktok_user_info": lambda params: self.ensembledata.tiktok_user_info(
                username=params.get("username", ""),
            ),
            "ensembledata_tiktok_user_posts": lambda params: self.ensembledata.tiktok_user_posts(
                username=params.get("username", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_tiktok_hashtag_posts": lambda params: self.ensembledata.tiktok_hashtag_posts(
                hashtag=params.get("hashtag", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_tiktok_keyword_posts": lambda params: self.ensembledata.tiktok_keyword_posts(
                keyword=params.get("keyword", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_tiktok_post_info": lambda params: self.ensembledata.tiktok_post_info(
                post_url=params.get("post_url", ""),
            ),
            "ensembledata_tiktok_comments": lambda params: self.ensembledata.tiktok_comments(
                post_url=params.get("post_url", ""),
                count=params.get("count", 30),
            ),
            # EnsembleData - Instagram
            "ensembledata_instagram_user_info": lambda params: self.ensembledata.instagram_user_info(
                username=params.get("username", ""),
            ),
            "ensembledata_instagram_user_posts": lambda params: self.ensembledata.instagram_user_posts(
                username=params.get("username", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_instagram_hashtag_posts": lambda params: self.ensembledata.instagram_hashtag_posts(
                hashtag=params.get("hashtag", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_instagram_post_info": lambda params: self.ensembledata.instagram_post_info(
                post_url=params.get("post_url", ""),
            ),
            "ensembledata_instagram_comments": lambda params: self.ensembledata.instagram_comments(
                post_url=params.get("post_url", ""),
                count=params.get("count", 30),
            ),
            # EnsembleData - YouTube
            "ensembledata_youtube_channel_info": lambda params: self.ensembledata.youtube_channel_info(
                channel_id=params.get("channel_id", ""),
            ),
            "ensembledata_youtube_channel_videos": lambda params: self.ensembledata.youtube_channel_videos(
                channel_id=params.get("channel_id", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_youtube_keyword_posts": lambda params: self.ensembledata.youtube_keyword_posts(
                keyword=params.get("keyword", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_youtube_video_info": lambda params: self.ensembledata.youtube_video_info(
                video_id=params.get("video_id", ""),
            ),
            "ensembledata_youtube_comments": lambda params: self.ensembledata.youtube_comments(
                video_id=params.get("video_id", ""),
                count=params.get("count", 30),
            ),
            # EnsembleData - Threads
            "ensembledata_threads_user_info": lambda params: self.ensembledata.threads_user_info(
                username=params.get("username", ""),
            ),
            "ensembledata_threads_user_posts": lambda params: self.ensembledata.threads_user_posts(
                username=params.get("username", ""),
                count=params.get("count", 30),
            ),
            "ensembledata_threads_keyword_posts": lambda params: self.ensembledata.threads_keyword_posts(
                keyword=params.get("keyword", ""),
                count=params.get("count", 30),
            ),
            # EnsembleData - Reddit (adicional)
            "ensembledata_reddit_subreddit_posts": lambda params: self.ensembledata.reddit_subreddit_posts(
                subreddit=params.get("subreddit", ""),
                count=params.get("count", 25),
            ),
            "ensembledata_reddit_comments": lambda params: self.ensembledata.reddit_comments(
                post_url=params.get("post_url", ""),
                count=params.get("count", 25),
            ),
            # EnsembleData - Twitter/X
            "ensembledata_twitter_user_info": lambda params: self.ensembledata.twitter_user_info(
                username=params.get("username", ""),
            ),
            "ensembledata_twitter_user_tweets": lambda params: self.ensembledata.twitter_user_tweets(
                username=params.get("username", ""),
                count=params.get("count", 20),
            ),
            "ensembledata_twitter_post_info": lambda params: self.ensembledata.twitter_post_info(
                tweet_url=params.get("tweet_url", ""),
            ),
            # EnsembleData - Twitch
            "ensembledata_twitch_keyword_posts": lambda params: self.ensembledata.twitch_keyword_posts(
                keyword=params.get("keyword", ""),
                count=params.get("count", 30),
            ),
            # EnsembleData - Snapchat
            "ensembledata_snapchat_user_info": lambda params: self.ensembledata.snapchat_user_info(
                username=params.get("username", ""),
            ),
        }

    async def _handle_query_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        detail = event.get("detail", {})
        query_type = detail.get("query_type")
        params = detail.get("params", {})
        handler = self._query_handlers.get(query_type)
        if not handler:
            return {"status": "error", "error": f"Unknown query type: {query_type}"}
        return await handler(params)

    async def _handle_result_created(self, event: Dict[str, Any]) -> Dict[str, Any]:
        detail = event.get("detail", {})
        case_id = detail.get("case_id")
        result_id = detail.get("result_id")
        if not case_id or not result_id:
            return {"status": "skipped", "reason": "missing case_id or result_id"}

        try:
            from services.ai_classification_service import AIClassificationService

            result = await self.db.execute(
                select(OSINTResult).where(OSINTResult.id == result_id)
            )
            osint_result = result.scalar_one_or_none()
            if not osint_result:
                return {"status": "skipped", "reason": "result not found"}

            classification_service = AIClassificationService(self.db)
            await classification_service.classify_osint_result(osint_result, case_id)
            await self.db.commit()
            return {"status": "success", "result_id": result_id}
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Error auto-classifying OSINT result {result_id}: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_ip_geolocation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from integrations.ipstack_api import IPStackAPIService

        ipstack = IPStackAPIService()
        return await ipstack.get_ip_info(
            ip_address=params.get("ip", ""),
            hostname=params.get("hostname", True),
            security=params.get("security", True),
        )
