"""
OSINT Service - Integration with OSINT tools
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from models.osint import OSINTQuery, OSINTResult
from integrations.news_api import NewsAPIService
from integrations.github_api import GitHubAPIService
from integrations.reddit_api import RedditAPIService
from integrations.shodan_api import ShodanAPIService
from integrations.wayback_api import WaybackAPIService
from integrations.dns_whois import DNSWhoisService

# INTEGRATIONS PENDENTS D'IMPLEMENTACIÓ REAL:
# - SherlockWrapper: requereix binari 'sherlock' al PATH (no disponible en prod)
# - ReconNGWrapper: requereix binari 'recon-ng' (no disponible en prod)
# - TheHarvesterWrapper: requereix binari 'theHarvester' (no disponible en prod)
# - EnsembleDataAPIService: endpoints no implementats (TODO pendent)
# Desactivades fins que s'implementin correctament.


def _unavailable(query_type: str, message: str) -> Dict[str, Any]:
    return {"status": "unavailable", "message": message, "query_type": query_type}


class OSINTService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sherlock = None  # Not implemented - requires system binary
        self.reconng = None  # Not implemented - requires system binary
        self.theharvester = None  # Not implemented - requires system binary
        self.ensembledata = None  # Not implemented - API endpoints pending
        self.news = NewsAPIService()
        self.github = GitHubAPIService()
        self.reddit = RedditAPIService()
        self.shodan = ShodanAPIService()
        self.wayback = WaybackAPIService()
        self.dns_whois = DNSWhoisService()

    async def execute_query(
        self,
        query_type: str,
        query_params: Dict[str, Any],
        case_id: int = None,
    ) -> Dict[str, Any]:
        """Execute OSINT query"""
        query = OSINTQuery(
            query_type=query_type,
            query_params=query_params,
            case_id=case_id,
            status="running",
        )
        self.db.add(query)
        await self.db.commit()
        await self.db.refresh(query)

        try:
            if query_type == "sherlock":
                result_data = _unavailable(
                    query_type,
                    "Sherlock no disponible en aquest entorn. Requereix binari instal·lat al PATH.",
                )
            elif query_type == "recon-ng":
                result_data = _unavailable(
                    query_type,
                    "Recon-ng no disponible en aquest entorn.",
                )
            elif query_type == "google_news":
                result_data = await self.news.search(
                    query=query_params.get("query", ""),
                    language=query_params.get("language", "es"),
                )
            elif query_type == "reddit":
                result_data = await self.reddit.search(
                    query=query_params.get("query", ""),
                    subreddit=query_params.get("subreddit"),
                )
            elif query_type == "github":
                result_data = await self.github.search(
                    query=query_params.get("query", ""),
                    type=query_params.get("type", "repositories"),
                )
            elif query_type == "theharvester":
                result_data = _unavailable(
                    query_type,
                    "TheHarvester no disponible en aquest entorn.",
                )
            elif query_type == "shodan":
                result_data = await self.shodan.search(
                    query=query_params.get("query", ""),
                    facets=query_params.get("facets"),
                    page=query_params.get("page", 1),
                )
            elif query_type == "shodan_host":
                result_data = await self.shodan.host_info(ip=query_params.get("ip", ""))
            elif query_type == "wayback":
                result_data = await self.wayback.get_snapshots(
                    url=query_params.get("url", ""),
                    limit=query_params.get("limit", 10),
                    from_date=query_params.get("from_date"),
                    to_date=query_params.get("to_date"),
                )
            elif query_type == "dns":
                result_data = await self.dns_whois.dns_lookup(
                    domain=query_params.get("domain", ""),
                    record_types=query_params.get("record_types"),
                )
            elif query_type == "whois":
                result_data = await self.dns_whois.whois_lookup(
                    domain=query_params.get("domain", ""),
                )
            elif query_type == "reverse_dns":
                result_data = await self.dns_whois.reverse_dns(ip=query_params.get("ip", ""))
            elif query_type == "ip_geolocation":
                from integrations.ipstack_api import IPStackAPIService

                ipstack = IPStackAPIService()
                result_data = await ipstack.get_ip_info(
                    ip_address=query_params.get("ip", ""),
                    hostname=query_params.get("hostname", True),
                    security=query_params.get("security", True),
                )
            elif query_type == "gdelt":
                from integrations.gdelt_api import GDELTAPIService

                gdelt = GDELTAPIService()
                result_data = await gdelt.search_events(
                    query=query_params.get("query", query_params.get("q", "")),
                    days=int(query_params.get("days", 7)),
                    max_results=int(query_params.get("max_results", 50)),
                )
            elif query_type == "rss_feed":
                from integrations.rss_feeds import RSSFeedsService

                rss = RSSFeedsService()
                result_data = await rss.fetch_feed(
                    source_key=query_params.get("source", "cfr"),
                    max_items=int(query_params.get("max_items", 20)),
                )
            elif query_type == "rss_all":
                from integrations.rss_feeds import RSSFeedsService

                rss = RSSFeedsService()
                result_data = await rss.fetch_all(
                    max_items_per_feed=int(query_params.get("max_items", 10)),
                )
            elif query_type == "rss_url":
                from integrations.rss_feeds import RSSFeedsService

                rss = RSSFeedsService()
                result_data = await rss.fetch_url(
                    feed_url=query_params.get("url", query_params.get("feed_url", "")),
                    max_items=int(query_params.get("max_items", 20)),
                    source_label=str(query_params.get("label", "curated")),
                    category=str(query_params.get("category", "curated")),
                )
            elif query_type == "opensanctions":
                from integrations.opensanctions_api import OpenSanctionsService

                os_svc = OpenSanctionsService()
                result_data = await os_svc.check_entity(
                    query_params.get("query", query_params.get("name", "")),
                )
            elif query_type.startswith("ensembledata_"):
                result_data = _unavailable(
                    query_type,
                    "EnsembleData no implementat. Endpoints pendents de confirmació amb el proveïdor.",
                )
            else:
                result_data = {"error": f"Unknown query type: {query_type}"}

            has_error = (
                isinstance(result_data, dict)
                and (
                    result_data.get("status") in ("error", "unavailable")
                    or result_data.get("error") is not None
                )
            )
            result_status = "error" if has_error else "completed"

            result = OSINTResult(
                query_id=query.id,
                data=result_data,
                status=result_status,
                error_message=(
                    result_data.get("error") or result_data.get("message")
                    if has_error
                    else None
                ),
            )
            self.db.add(result)
            await self.db.flush()

            query.status = "completed"
            await self.db.commit()

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

            return {
                "query_id": query.id,
                "result_id": result.id,
                "data": result_data,
                "status": result_status,
                "error": (
                    (result_data.get("error") or result_data.get("message"))
                    if has_error
                    else None
                ),
            }

        except Exception as e:
            query.status = QueryStatus.FAILED
            query.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return {
                "query_id": query.id,
                "error": str(e),
                "status": "failed",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "message": "Error ejecutando consulta OSINT",
                },
            }
