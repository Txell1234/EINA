"""
Run Tavily searches and persist as case OSINT (same pipeline as manual collection).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.osint_data_utils import extract_search_keywords, flatten_osint_items
from services.osint_service import OSINTService
from services.tavily_pipeline_service import (
    crawl_preferred_domains_for_case,
    run_tavily_research_for_case,
    tavily_configured,
)

logger = logging.getLogger(__name__)


def build_tavily_queries(text: str, hypothesis: str = "", *, max_queries: int = 3) -> list[str]:
    """Derive 1–3 search queries from premise text and optional hypothesis."""
    from services.osint_data_utils import build_osint_search_queries

    return build_osint_search_queries(
        case_name=hypothesis[:120] if hypothesis else text[:120],
        case_description=text,
        extra_context=hypothesis,
        max_queries=max_queries,
    )


async def collect_tavily_for_case(
    db: AsyncSession,
    case_id: int,
    text: str,
    hypothesis: str = "",
    *,
    max_results: int = 10,
    max_queries: int = 3,
    search_depth: str = "advanced",
    topic: str = "news",
    run_research: bool = False,
    run_preferred_crawl: bool = False,
) -> dict[str, Any]:
    """
    Execute Tavily collection linked to case_id: Search (+ optional Research + preferred Crawl).
    """
    if not tavily_configured():
        return {
            "status": "skipped",
            "reason": "TAVILY_API_KEY no configurada",
            "queries_run": 0,
            "articles_collected": 0,
        }

    queries = (
        build_tavily_queries(text, hypothesis, max_queries=max_queries)
        if max_queries > 0
        else []
    )
    if not queries and not run_research and not run_preferred_crawl:
        return {
            "status": "skipped",
            "reason": "No s'han pogut generar consultes de cerca",
            "queries_run": 0,
            "articles_collected": 0,
        }

    osint = OSINTService(db)
    runs: list[dict[str, Any]] = []
    total_articles = 0

    for q in queries:
        try:
            result = await osint.execute_query(
                query_type="tavily",
                query_params={
                    "query": q,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "topic": topic,
                },
                case_id=case_id,
            )
            data = result.get("data") or {}
            n = len(flatten_osint_items(data)) if isinstance(data, dict) else 0
            total_articles += n
            runs.append(
                {
                    "query": q,
                    "query_id": result.get("query_id"),
                    "result_id": result.get("result_id"),
                    "status": result.get("status"),
                    "articles": n,
                    "error": result.get("error"),
                    "kind": "search",
                }
            )
        except Exception as exc:
            logger.warning("Tavily OSINT query failed for case %s: %s", case_id, exc)
            runs.append({"query": q, "status": "error", "error": str(exc), "articles": 0, "kind": "search"})

    research_summary: dict[str, Any] | None = None
    if run_research:
        research_summary = await run_tavily_research_for_case(
            db, case_id, text, hypothesis
        )
        total_articles += int(research_summary.get("articles_collected") or 0)
        runs.append({**research_summary, "kind": "research"})

    crawl_summary: dict[str, Any] | None = None
    if run_preferred_crawl:
        crawl_summary = await crawl_preferred_domains_for_case(
            db, case_id, text, hypothesis
        )
        total_articles += int(crawl_summary.get("articles_collected") or 0)
        runs.append({**crawl_summary, "kind": "crawl"})

    return {
        "status": "success",
        "queries_run": len([r for r in runs if r.get("kind") == "search"]),
        "articles_collected": total_articles,
        "queries": queries,
        "runs": runs,
        "research": research_summary,
        "crawl": crawl_summary,
        "provider": "tavily",
    }
