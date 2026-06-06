"""
OSINT Service - Integration with OSINT tools
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.config import settings
from models.osint import OSINTQuery, OSINTResult, QueryStatus
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
# - EnsembleData: via integrations/ensembledata_osint.py (requereix ENSEMBLEDATA_API_KEY)


def _unavailable(query_type: str, message: str) -> Dict[str, Any]:
    return {"status": "unavailable", "message": message, "query_type": query_type}


class OSINTService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sherlock = None  # Not implemented - requires system binary
        self.reconng = None  # Not implemented - requires system binary
        self.theharvester = None  # Not implemented - requires system binary
        from integrations.ensembledata_api import EnsembleDataAPIService

        self.ensembledata = EnsembleDataAPIService()
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
        if case_id is None:
            import logging
            logging.getLogger(__name__).warning(
                "OSINT query %s sense case_id — les dades no entraran a l'extracció del cas",
                query_type,
            )

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
            elif query_type == "gdelt_gfg":
                from integrations.gdelt_gfg import GDELTGFGService

                gfg = GDELTGFGService()
                result_data = await gfg.search_frontpage(
                    query=query_params.get("query", query_params.get("q", "")),
                    max_results=int(query_params.get("max_results", 40)),
                    domain=str(query_params.get("domain") or ""),
                )
            elif query_type == "tavily":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                result_data = await tavily.search(
                    query=query_params.get("query", query_params.get("q", "")),
                    max_results=int(query_params.get("max_results", 10)),
                    search_depth=str(query_params.get("search_depth") or "advanced"),
                    topic=str(query_params.get("topic") or "news"),
                    include_domains=query_params.get("include_domains"),
                    exclude_domains=query_params.get("exclude_domains"),
                )
            elif query_type == "tavily_extract":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                urls = query_params.get("urls") or []
                if isinstance(urls, str):
                    urls = [u.strip() for u in urls.split(",") if u.strip()]
                result_data = await tavily.extract(
                    list(urls),
                    extract_depth=str(query_params.get("extract_depth") or "basic"),
                    format=str(query_params.get("format") or "markdown"),
                )
            elif query_type == "tavily_crawl":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                result_data = await tavily.crawl(
                    str(query_params.get("url") or ""),
                    instructions=query_params.get("instructions"),
                    max_depth=int(query_params.get("max_depth", 1)),
                    max_breadth=int(query_params.get("max_breadth", 20)),
                    limit=int(query_params.get("limit", 50)),
                    extract_depth=str(query_params.get("extract_depth") or "basic"),
                )
            elif query_type == "tavily_map":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                result_data = await tavily.map_site(
                    str(query_params.get("url") or ""),
                    instructions=query_params.get("instructions"),
                    max_depth=int(query_params.get("max_depth", 1)),
                    max_breadth=int(query_params.get("max_breadth", 20)),
                    limit=int(query_params.get("limit", 50)),
                )
            elif query_type == "tavily_research":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                wait = query_params.get("wait", True)
                if wait in (False, "false", "0", 0):
                    result_data = await tavily.create_research(
                        str(query_params.get("input") or query_params.get("query") or ""),
                        model=str(query_params.get("model") or "auto"),
                    )
                else:
                    result_data = await tavily.research_and_wait(
                        str(query_params.get("input") or query_params.get("query") or ""),
                        model=str(query_params.get("model") or "auto"),
                        max_wait_seconds=int(query_params.get("max_wait_seconds", 300)),
                    )
            elif query_type == "tavily_research_get":
                from integrations.tavily_api import TavilyAPIService

                tavily = TavilyAPIService()
                result_data = await tavily.get_research(
                    str(query_params.get("request_id") or ""),
                )
            elif query_type == "nikkei":
                from integrations.nikkei_service import NikkeiService

                nikkei = NikkeiService()
                mode = str(query_params.get("mode") or "").strip().lower()
                if mode == "latest" or not query_params.get("url"):
                    result_data = await nikkei.fetch_latest(
                        max_items=int(query_params.get("max_results", 10)),
                    )
                else:
                    url = str(query_params.get("url") or "")
                    urls = query_params.get("urls") or ([url] if url else [])
                    result_data = await nikkei.scrape_urls(
                        list(urls),
                        max_items=int(query_params.get("max_results", 10)),
                    )
            elif query_type == "bloomberg":
                from integrations.bloomberg_service import BloombergService

                bb = BloombergService()
                edition = str(query_params.get("edition") or "global")
                url = str(query_params.get("url") or "").strip()
                mode = str(query_params.get("mode") or "").strip().lower()
                if mode == "latest" or not url:
                    result_data = await bb.fetch_latest(
                        edition=edition,
                        max_items=int(query_params.get("max_results", 15)),
                    )
                else:
                    urls = query_params.get("urls") or [url]
                    result_data = await bb.scrape_urls(
                        list(urls),
                        edition=edition,
                        max_items=int(query_params.get("max_results", 10)),
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
                from integrations.ensembledata_osint import execute_ensembledata_query

                result_data = await execute_ensembledata_query(query_type, query_params)
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
                scope = scope_from_query_params(query_params)
                if scope and (scope.apply_topic_filter or scope.domains or scope.start_date or scope.period_days):
                    try:
                        from services.analysis_scope_service import apply_scope_to_osint_result

                        await apply_scope_to_osint_result(self.db, result.id, case_id, scope)
                        await self.db.refresh(result)
                        if isinstance(result_data, dict):
                            result_data = result.data
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            "Scope filter failed for result %s: %s", result.id, e
                        )
                else:
                    try:
                        from services.analysis_scope_service import auto_apply_scope_for_case_result

                        await auto_apply_scope_for_case_result(self.db, result.id, case_id)
                        await self.db.refresh(result)
                        if isinstance(result_data, dict):
                            result_data = result.data
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            "Auto scope filter failed for result %s: %s", result.id, e
                        )

            if case_id and not has_error:
                try:
                    from services.tavily_pipeline_service import post_tavily_pipeline_hook

                    await post_tavily_pipeline_hook(
                        self.db,
                        result.id,
                        query_type,
                        query_params,
                        case_id=case_id,
                    )
                    await self.db.refresh(result)
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Tavily pipeline hook failed for result %s: %s", result.id, e
                    )

            if case_id and not has_error:
                try:
                    from services.tavily_pipeline_service import post_tavily_viz_hook

                    await post_tavily_viz_hook(
                        self.db,
                        result.id,
                        query_type,
                        case_id=case_id,
                    )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Viz hook failed for result %s: %s", result.id, e
                    )

            if case_id and not has_error:
                try:
                    from services.osint_repair_service import post_query_enrichment_hook

                    await post_query_enrichment_hook(
                        self.db,
                        result.id,
                        max_items=int(getattr(settings, "OSINT_POST_ENRICH_MAX_ITEMS", 5)),
                    )
                    await self.db.refresh(result)
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Post-query enrichment failed for result %s: %s", result.id, e
                    )

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

            coverage_hint = None
            if case_id and not has_error:
                try:
                    from services.extraction_coverage_service import get_extraction_coverage

                    cov = await get_extraction_coverage(self.db, case_id)
                    coverage_hint = {
                        "pending_extraction": cov["articles"]["pending_extraction"],
                        "coverage_percent": cov["coverage_percent"],
                    }
                except Exception:
                    pass

            return {
                "query_id": query.id,
                "result_id": result.id,
                "data": result.data if isinstance(result.data, dict) else result_data,
                "status": result_status,
                "error": (
                    (result_data.get("error") or result_data.get("message"))
                    if has_error
                    else None
                ),
                "coverage": coverage_hint,
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
