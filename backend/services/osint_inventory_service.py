"""Human-friendly OSINT inventory per case — sources, articles, research briefs."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import CasePrompt
from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult
from services.extraction_coverage_service import collect_case_articles
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item

QUERY_TYPE_LABELS: dict[str, str] = {
    "gdelt": "GDELT",
    "gdelt_gfg": "GDELT Portades (GFG)",
    "tavily": "Tavily (cerca web)",
    "tavily_extract": "Tavily Extract",
    "tavily_crawl": "Tavily Crawl",
    "tavily_map": "Tavily Map",
    "tavily_research": "Tavily Research",
    "rss_feed": "Think tank / RSS",
    "rss_all": "RSS (tots els feeds)",
    "rss_url": "RSS (URL)",
    "bloomberg": "Bloomberg",
    "nikkei": "Nikkei Asia",
    "google_news": "Google News",
    "reddit": "Reddit",
    "github": "GitHub",
}

RSS_SOURCE_LABELS: dict[str, str] = {
    "cfr": "Council on Foreign Relations",
    "iiss": "IISS",
    "chatham_house": "Chatham House",
    "rand": "RAND Corporation",
    "csis": "CSIS",
    "icg": "International Crisis Group",
    "brookings": "Brookings Institution",
    "elcano": "Real Instituto Elcano",
    "foreign_affairs": "Foreign Affairs",
    "ecfr": "ECFR",
}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or ""
    except Exception:
        return ""


def _params_summary(query_type: str, params: dict[str, Any] | None) -> str:
    p = params or {}
    if query_type == "rss_feed":
        key = str(p.get("source") or "")
        return RSS_SOURCE_LABELS.get(key, key or "feed")
    if query_type in ("gdelt", "tavily", "google_news", "gdelt_gfg"):
        return str(p.get("query") or p.get("q") or "")[:120]
    if query_type == "tavily_research":
        return str(p.get("input") or "")[:120]
    if query_type == "bloomberg":
        return f"{p.get('edition', 'global')} · {p.get('mode', 'latest')}"
    if query_type == "nikkei":
        return str(p.get("url") or "darrers titulars")[:120]
    return query_type


def _article_row(art: dict[str, Any], extracted_urls: set[str]) -> dict[str, Any]:
    url = str(art.get("url") or "").strip()
    text_len = len(text_from_osint_item(art).strip())
    return {
        "title": str(art.get("title") or "Sense titular")[:200],
        "url": url,
        "domain": _domain(url),
        "date": str(art.get("date") or art.get("published_date") or "")[:19],
        "source": str(art.get("source") or art.get("query_type") or ""),
        "summary": str(art.get("summary") or "")[:280],
        "text_len": text_len,
        "enriched": bool(art.get("enriched")),
        "extracted": bool(url and url in extracted_urls),
        "frontpage_score": float(art.get("frontpage_score") or art.get("importance_score") or 0),
    }


async def get_case_osint_inventory(
    db: AsyncSession,
    case_id: int,
    *,
    max_articles_per_query: int = 15,
    max_queries: int = 40,
) -> dict[str, Any]:
    ext_r = await db.execute(
        select(ExtractedStatement.source_url).where(ExtractedStatement.case_id == case_id)
    )
    extracted_urls = {u for (u,) in ext_r.all() if u and not str(u).startswith("direct-analysis:")}

    q_r = await db.execute(
        select(OSINTQuery)
        .where(OSINTQuery.case_id == case_id)
        .order_by(OSINTQuery.created_at.desc())
        .limit(max_queries)
    )
    queries = list(q_r.scalars().all())

    groups: dict[str, dict[str, Any]] = {}
    research_briefs: list[dict[str, Any]] = []
    total_articles = 0

    for q in queries:
        qtype = q.query_type or "unknown"
        label = QUERY_TYPE_LABELS.get(qtype, qtype.replace("_", " ").title())
        if qtype not in groups:
            groups[qtype] = {
                "query_type": qtype,
                "label": label,
                "query_count": 0,
                "article_count": 0,
                "runs": [],
            }
        groups[qtype]["query_count"] += 1

        res_r = await db.execute(
            select(OSINTResult)
            .where(OSINTResult.query_id == q.id)
            .order_by(OSINTResult.created_at.desc())
            .limit(1)
        )
        result = res_r.scalar_one_or_none()
        data = result.data if result and isinstance(result.data, dict) else {}
        has_error = osint_has_error(data) if data else True

        run: dict[str, Any] = {
            "query_id": q.id,
            "result_id": result.id if result else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "params_summary": _params_summary(qtype, q.query_params if isinstance(q.query_params, dict) else {}),
            "status": result.status if result else q.status,
            "error": (data.get("error") or data.get("message")) if has_error and data else None,
            "article_count": 0,
            "articles": [],
            "research_report": None,
            "scope_filter": data.get("_scope_filter") if isinstance(data, dict) else None,
        }

        if qtype in ("tavily_research", "tavily_research_get") and data and not has_error:
            report = str(data.get("research_report") or "").strip()
            if report:
                run["research_report"] = {
                    "excerpt": report[:600] + ("…" if len(report) > 600 else ""),
                    "full_length": len(report),
                    "source_count": len(data.get("sources") or []),
                    "request_id": data.get("request_id"),
                }
                research_briefs.append(
                    {
                        "query_id": q.id,
                        "result_id": result.id if result else None,
                        "created_at": run["created_at"],
                        "excerpt": run["research_report"]["excerpt"],
                        "source_count": run["research_report"]["source_count"],
                    }
                )

        if data and not has_error:
            flat = flatten_osint_items(data)
            if not flat and qtype == "tavily_map":
                urls = data.get("urls") or data.get("results") or []
                if isinstance(urls, list):
                    flat = [{"title": str(u), "url": str(u), "source": "tavily_map"} for u in urls[:max_articles_per_query]]

            articles = [_article_row(a, extracted_urls) for a in flat[:max_articles_per_query]]
            run["articles"] = articles
            run["article_count"] = len(flat)
            total_articles += len(flat)
            groups[qtype]["article_count"] += len(flat)

        groups[qtype]["runs"].append(run)

    prompt_r = await db.execute(
        select(CasePrompt)
        .where(CasePrompt.case_id == case_id)
        .order_by(CasePrompt.created_at.desc())
        .limit(5)
    )
    for row in prompt_r.scalars().all():
        meta = row.ai_analysis if isinstance(row.ai_analysis, dict) else {}
        if meta.get("tavily_research") and row.prompt:
            research_briefs.append(
                {
                    "from_case_prompt": True,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "excerpt": row.prompt[:600] + ("…" if len(row.prompt) > 600 else ""),
                    "source_count": meta.get("source_count", 0),
                }
            )

    all_articles = await collect_case_articles(db, case_id)
    by_domain: dict[str, int] = {}
    for a in all_articles:
        d = _domain(str(a.get("url") or "")) or str(a.get("source") or "unknown")
        by_domain[d] = by_domain.get(d, 0) + 1
    top_domains = sorted(by_domain.items(), key=lambda x: -x[1])[:10]

    pending = sum(1 for a in all_articles if str(a.get("url") or "") and str(a.get("url")) not in extracted_urls)
    extracted_n = len(extracted_urls)

    actions: list[str] = []
    if pending > 0:
        actions.append(f"Extreure {pending} articles pendents (Pas 0 prospectiu o «Extreure tot el pendent»).")
    if any(g["query_type"] == "tavily_research" for g in groups.values()) and not research_briefs:
        actions.append("Recerca Tavily en curs o sense informe — torna a obrir el resultat.")
    if not queries:
        actions.append("Encara no hi ha consultes OSINT per aquest cas — usa Recollida OSINT.")
    if not actions:
        actions.append("Revisa declaracions extretes i executa el pipeline d'intel·ligència.")

    return {
        "case_id": case_id,
        "summary": {
            "total_queries": len(queries),
            "total_articles": total_articles,
            "unique_articles": len({str(a.get("url") or a.get("title")) for a in all_articles}),
            "extracted_urls": extracted_n,
            "pending_extraction": pending,
            "research_reports": len(research_briefs),
            "top_domains": [{"domain": d, "count": c} for d, c in top_domains],
        },
        "source_groups": sorted(groups.values(), key=lambda g: -g["article_count"]),
        "research_briefs": research_briefs[:5],
        "recommended_actions": actions,
    }
