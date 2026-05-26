"""
Tavily pipeline orchestration — Map→Extract, Search→Extract, preferred-domain Crawl, Research briefs.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from integrations.tavily_api import TavilyAPIService
from models.case import CasePrompt
from models.osint import OSINTResult
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item
from services.osint_repair_service import merge_enriched_into_payload

logger = logging.getLogger(__name__)

_TAVILY_QUERY_TYPES = frozenset(
    {
        "tavily",
        "tavily_extract",
        "tavily_crawl",
        "tavily_map",
        "tavily_research",
        "tavily_research_get",
    }
)


def tavily_configured() -> bool:
    return TavilyAPIService().configured()


def preferred_domains_list() -> list[str]:
    raw = getattr(settings, "GEOPOLITICS_PREFERRED_DOMAINS", "") or ""
    return [d.strip().lower() for d in raw.split(",") if d.strip()]


def _domain_score(url: str) -> float:
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    except Exception:
        return 0.0
    host = host.removeprefix("www.")
    for i, dom in enumerate(preferred_domains_list()):
        if host == dom or host.endswith(f".{dom}"):
            return 100.0 - i
    return 0.0


def rank_urls_for_extraction(urls: list[str], *, keywords: str = "") -> list[str]:
    """Sort URLs: preferred domains first, then keyword overlap in path."""
    kw = [w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", keywords.lower())[:8]]

    def _score(u: str) -> float:
        base = _domain_score(u)
        path = urlparse(u).path.lower()
        base += sum(2.0 for k in kw if k in path)
        return base

    unique = list(dict.fromkeys(u.strip() for u in urls if u and str(u).strip()))
    return sorted(unique, key=_score, reverse=True)


def select_crawl_seeds(text: str, hypothesis: str = "", *, max_seeds: int = 2) -> list[dict[str, str]]:
    """Pick 1–2 preferred domains to crawl based on case text."""
    haystack = f"{text} {hypothesis}".lower()
    seeds: list[dict[str, str]] = []
    instructions = (hypothesis or text)[:200].strip()

    for dom in preferred_domains_list():
        token = dom.split(".")[0]
        if token in haystack or dom.replace(".", " ") in haystack:
            seeds.append(
                {
                    "url": f"https://{dom}",
                    "instructions": instructions or f"Pages related to {token}",
                }
            )
        if len(seeds) >= max_seeds:
            break

    if not seeds:
        for dom in preferred_domains_list()[:max_seeds]:
            seeds.append(
                {
                    "url": f"https://{dom}",
                    "instructions": instructions or "Recent geopolitical analysis",
                }
            )
    return seeds[:max_seeds]


async def _load_result(db: AsyncSession, result_id: int) -> OSINTResult | None:
    r = await db.execute(select(OSINTResult).where(OSINTResult.id == result_id))
    return r.scalar_one_or_none()


async def extract_urls_into_result(
    db: AsyncSession,
    result_id: int,
    urls: list[str],
    *,
    max_urls: int = 8,
) -> dict[str, Any]:
    """Run Tavily Extract on URLs and merge bodies into an existing OSINTResult."""
    if not urls or not tavily_configured():
        return {"extracted": 0, "result_id": result_id}

    result = await _load_result(db, result_id)
    if not result or not isinstance(result.data, dict) or osint_has_error(result.data):
        return {"extracted": 0, "result_id": result_id}

    ranked = rank_urls_for_extraction(urls)[:max_urls]
    tavily = TavilyAPIService()
    ext = await tavily.extract(ranked, extract_depth="advanced")
    if ext.get("status") != "success":
        return {"extracted": 0, "result_id": result_id, "error": ext.get("error")}

    by_url = {
        str(a.get("url") or "").strip(): a
        for a in ext.get("articles") or []
        if a.get("url")
    }
    if not by_url:
        return {"extracted": 0, "result_id": result_id}

    enriched = {
        u: {
            **a,
            "body": a.get("body") or a.get("summary") or "",
            "enriched": True,
            "enrichment_source": "tavily_extract",
        }
        for u, a in by_url.items()
    }
    result.data = merge_enriched_into_payload(result.data, enriched)

    # Append new articles for map-only URLs not in payload
    existing_urls = {str(i.get("url") or "") for i in flatten_osint_items(result.data)}
    new_articles = []
    for url, art in enriched.items():
        if url not in existing_urls:
            new_articles.append(
                {
                    "title": art.get("title") or url,
                    "url": url,
                    "body": art.get("body") or "",
                    "summary": (art.get("body") or "")[:500],
                    "source": "tavily_extract",
                    "provider": "tavily_extract",
                    "enriched": True,
                }
            )
    if new_articles:
        payload = copy.deepcopy(result.data)
        payload.setdefault("articles", [])
        if isinstance(payload["articles"], list):
            payload["articles"].extend(new_articles)
            payload["count"] = len(flatten_osint_items(payload))
        result.data = payload

    await db.commit()
    return {"extracted": len(enriched), "result_id": result_id, "urls": list(enriched.keys())}


async def post_tavily_pipeline_hook(
    db: AsyncSession,
    result_id: int | None,
    query_type: str,
    query_params: dict[str, Any] | None,
    *,
    case_id: int | None = None,
) -> None:
    """Run Tavily-specific post-processing after a successful OSINT query."""
    if not result_id or not tavily_configured():
        return
    if query_type not in _TAVILY_QUERY_TYPES:
        return

    qparams = query_params or {}
    try:
        if query_type == "tavily_map":
            result = await _load_result(db, result_id)
            if not result or not isinstance(result.data, dict):
                return
            urls = [
                str(i.get("url") or "")
                for i in flatten_osint_items(result.data)
                if i.get("url")
            ]
            kw = str(qparams.get("instructions") or qparams.get("url") or "")
            max_ext = int(getattr(settings, "TAVILY_MAP_EXTRACT_MAX_URLS", 8))
            await extract_urls_into_result(
                db, result_id, rank_urls_for_extraction(urls, keywords=kw), max_urls=max_ext
            )

        elif query_type == "tavily":
            result = await _load_result(db, result_id)
            if not result or not isinstance(result.data, dict):
                return
            items = flatten_osint_items(result.data)
            thin_urls = [
                str(i.get("url") or "")
                for i in items
                if str(i.get("url") or "").strip()
                and len(text_from_osint_item(i).strip()) < 250
            ]
            if thin_urls:
                max_ext = int(getattr(settings, "TAVILY_SEARCH_EXTRACT_MAX_URLS", 5))
                kw = str(qparams.get("query") or qparams.get("q") or "")
                await extract_urls_into_result(
                    db,
                    result_id,
                    rank_urls_for_extraction(thin_urls, keywords=kw),
                    max_urls=max_ext,
                )

        elif query_type == "tavily_research":
            result = await _load_result(db, result_id)
            if not result or not isinstance(result.data, dict):
                return
            report = str(result.data.get("research_report") or "").strip()
            if report and case_id:
                await persist_research_brief(
                    db,
                    case_id,
                    report,
                    result.data.get("sources") or [],
                    str(result.data.get("request_id") or ""),
                )
                from services.case_recalc_service import maybe_recalc_after_data_change

                await maybe_recalc_after_data_change(db, case_id, reason="tavily_research")

    except Exception as exc:
        logger.warning("Tavily pipeline hook failed for result %s: %s", result_id, exc)


async def persist_research_brief(
    db: AsyncSession,
    case_id: int,
    report_text: str,
    sources: list[Any],
    request_id: str = "",
) -> None:
    """Store Tavily research report as CasePrompt for reports and Godet context."""
    if not report_text.strip():
        return

    source_lines = []
    for s in sources[:20]:
        if isinstance(s, dict):
            title = s.get("title") or s.get("url") or ""
            url = s.get("url") or ""
            if url:
                source_lines.append(f"- {title}: {url}")

    prompt_body = report_text.strip()
    if source_lines:
        prompt_body += "\n\n## Fonts Tavily Research\n" + "\n".join(source_lines)
    if request_id:
        prompt_body += f"\n\n_request_id: {request_id}_"

    existing_r = await db.execute(
        select(CasePrompt)
        .where(CasePrompt.case_id == case_id)
        .order_by(CasePrompt.created_at.desc())
        .limit(1)
    )
    row = existing_r.scalar_one_or_none()
    meta = {"tavily_research": True, "request_id": request_id, "source_count": len(sources)}

    if row and row.ai_analysis and isinstance(row.ai_analysis, dict):
        if row.ai_analysis.get("tavily_research"):
            row.prompt = prompt_body
            merged = dict(row.ai_analysis)
            merged.update(meta)
            row.ai_analysis = merged
        else:
            db.add(
                CasePrompt(
                    case_id=case_id,
                    prompt=prompt_body,
                    ai_analysis=meta,
                )
            )
    elif row:
        db.add(
            CasePrompt(
                case_id=case_id,
                prompt=prompt_body,
                ai_analysis=meta,
            )
        )
    else:
        db.add(
            CasePrompt(
                case_id=case_id,
                prompt=prompt_body,
                ai_analysis=meta,
            )
        )
    await db.commit()


async def crawl_preferred_domains_for_case(
    db: AsyncSession,
    case_id: int,
    text: str,
    hypothesis: str = "",
) -> dict[str, Any]:
    """Crawl 1–2 preferred domains and persist as case OSINT."""
    if not tavily_configured():
        return {"status": "skipped", "reason": "TAVILY_API_KEY no configurada"}

    from services.osint_service import OSINTService

    seeds = select_crawl_seeds(text, hypothesis, max_seeds=2)
    if not seeds:
        return {"status": "skipped", "reason": "Cap domini seed"}

    osint = OSINTService(db)
    limit = int(getattr(settings, "TAVILY_PREFERRED_CRAWL_LIMIT", 25))
    runs: list[dict[str, Any]] = []
    total = 0

    for seed in seeds:
        try:
            res = await osint.execute_query(
                query_type="tavily_crawl",
                query_params={
                    "url": seed["url"],
                    "instructions": seed.get("instructions"),
                    "limit": limit,
                    "max_depth": 1,
                },
                case_id=case_id,
            )
            data = res.get("data") or {}
            n = len(flatten_osint_items(data)) if isinstance(data, dict) else 0
            total += n
            runs.append({"url": seed["url"], "articles": n, "status": res.get("status")})
        except Exception as exc:
            logger.warning("Preferred crawl failed for %s: %s", seed["url"], exc)
            runs.append({"url": seed["url"], "status": "error", "error": str(exc)})

    return {
        "status": "success",
        "seeds": len(seeds),
        "articles_collected": total,
        "runs": runs,
        "provider": "tavily_crawl",
    }


async def run_tavily_research_for_case(
    db: AsyncSession,
    case_id: int,
    text: str,
    hypothesis: str = "",
    *,
    model: str = "auto",
) -> dict[str, Any]:
    """Deep Tavily Research → OSINT + CasePrompt brief."""
    if not tavily_configured():
        return {"status": "skipped", "reason": "TAVILY_API_KEY no configurada"}

    from services.osint_data_utils import extract_search_keywords
    from services.osint_service import OSINTService

    topic = extract_search_keywords(hypothesis or text[:400], hypothesis or text[:80])
    input_text = f"{topic}\n\nContext:\n{text[:1500]}"
    if hypothesis:
        input_text = f"Hypothesis: {hypothesis[:400]}\n\n{input_text}"

    max_wait = int(getattr(settings, "TAVILY_RESEARCH_MAX_WAIT_SECONDS", 300))
    osint = OSINTService(db)
    res = await osint.execute_query(
        query_type="tavily_research",
        query_params={
            "input": input_text[:4000],
            "model": model,
            "wait": True,
            "max_wait_seconds": max_wait,
        },
        case_id=case_id,
    )
    data = res.get("data") or {}
    pending = bool(data.get("pending"))
    articles = len(flatten_osint_items(data)) if isinstance(data, dict) else 0

    return {
        "status": "success" if not pending else "pending",
        "research_status": data.get("research_status"),
        "request_id": data.get("request_id"),
        "articles_collected": articles,
        "has_report": bool(data.get("research_report")),
        "query_id": res.get("query_id"),
        "result_id": res.get("result_id"),
        "provider": "tavily_research",
    }


_TAVILY_VIZ_TYPES = frozenset(
    {
        "tavily",
        "tavily_extract",
        "tavily_crawl",
        "tavily_map",
        "tavily_research",
        "tavily_research_get",
        "gdelt",
        "gdelt_gfg",
        "google_news",
    }
)


async def post_tavily_viz_hook(
    db: AsyncSession,
    result_id: int | None,
    query_type: str,
    *,
    case_id: int | None = None,
) -> dict[str, Any]:
    """
    After OSINT collection: extract timeline events for map/heatmap/timeline views.
    Runs for Tavily and other geo-relevant sources when enabled.
    """
    if not result_id or not case_id:
        return {"events_extracted": 0}
    if query_type not in _TAVILY_VIZ_TYPES:
        return {"events_extracted": 0}

    auto = getattr(settings, "TAVILY_AUTO_EXTRACT_EVENTS", True)
    if not auto:
        return {"events_extracted": 0, "skipped": True}

    try:
        from services.diplomatic_event_service import DiplomaticEventService

        svc = DiplomaticEventService(db)
        events = await svc.extract_events_for_osint_result(result_id, case_id)
        if events:
            await db.commit()
        return {"events_extracted": len(events), "result_id": result_id}
    except Exception as exc:
        logger.warning("Viz event extraction failed for result %s: %s", result_id, exc)
        return {"events_extracted": 0, "error": str(exc)}
