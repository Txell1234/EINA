"""
Repair and post-process OSINT data (orphan queries, in-result enrichment).
"""
from __future__ import annotations

import copy
import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.osint import OSINTQuery, OSINTResult
from services.article_enrichment_service import enrich_osint_items
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item

logger = logging.getLogger(__name__)


def merge_enriched_into_payload(data: dict[str, Any], enriched_by_url: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return a copy of OSINT payload with enriched article fields merged by URL."""
    if not enriched_by_url or not isinstance(data, dict):
        return data

    payload = copy.deepcopy(data)

    def _merge_item(item: dict[str, Any]) -> None:
        url = str(item.get("url") or item.get("link") or "").strip()
        scraped = enriched_by_url.get(url)
        if not scraped:
            return
        body = str(scraped.get("body") or scraped.get("summary") or "").strip()
        if body:
            item["body"] = body
            item["summary"] = body[:500]
            item["enriched"] = True
            item["enrichment_source"] = scraped.get("enrichment_source") or scraped.get("provider", "fetcher")
        if scraped.get("title") and not item.get("title"):
            item["title"] = scraped["title"]

    for key in ("articles", "items", "results"):
        lst = payload.get(key)
        if isinstance(lst, list):
            for item in lst:
                if isinstance(item, dict):
                    _merge_item(item)

    sources = payload.get("sources")
    if isinstance(sources, dict):
        for source_data in sources.values():
            if not isinstance(source_data, dict):
                continue
            nested = source_data.get("items") or source_data.get("articles")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        _merge_item(item)

    return payload


async def repair_orphan_queries(db: AsyncSession, target_case_id: int) -> dict[str, Any]:
    """Attach OSINT queries with case_id=NULL to target_case_id."""
    count_r = await db.execute(
        select(OSINTQuery.id).where(OSINTQuery.case_id.is_(None))
    )
    ids = [row[0] for row in count_r.all()]
    if not ids:
        return {"repaired": 0, "case_id": target_case_id}

    await db.execute(
        update(OSINTQuery).where(OSINTQuery.id.in_(ids)).values(case_id=target_case_id)
    )
    await db.commit()
    logger.info("Repaired %d orphan OSINT queries → case %s", len(ids), target_case_id)
    return {"repaired": len(ids), "case_id": target_case_id}


async def enrich_osint_result_record(
    db: AsyncSession,
    result_id: int,
    *,
    max_items: int = 5,
) -> dict[str, Any]:
    """Enrich short articles inside one OSINTResult row and persist."""
    r = await db.execute(select(OSINTResult).where(OSINTResult.id == result_id))
    result = r.scalar_one_or_none()
    if not result or not isinstance(result.data, dict) or osint_has_error(result.data):
        return {"enriched": 0, "result_id": result_id}

    items = flatten_osint_items(result.data)
    short = [
        art for art in items
        if str(art.get("url") or "").strip()
        and len(text_from_osint_item(art).strip()) < 200
    ]
    short.sort(
        key=lambda a: -float(a.get("frontpage_score") or a.get("importance_score") or 0)
    )
    if not short:
        return {"enriched": 0, "result_id": result_id}

    batch = short[:max_items]
    enriched_list = await enrich_osint_items(batch)
    by_url = {str(a.get("url") or "").strip(): a for a in enriched_list if a.get("url")}
    actually = {u: a for u, a in by_url.items() if a.get("enriched") or len(text_from_osint_item(a)) >= 200}
    if not actually:
        return {"enriched": 0, "result_id": result_id}

    result.data = merge_enriched_into_payload(result.data, actually)
    await db.commit()
    return {"enriched": len(actually), "result_id": result_id}


async def post_query_enrichment_hook(
    db: AsyncSession,
    result_id: int | None,
    *,
    max_items: int = 5,
) -> None:
    """Best-effort enrichment after a successful OSINT query."""
    if not result_id:
        return
    try:
        await enrich_osint_result_record(db, result_id, max_items=max_items)
    except Exception as exc:
        logger.warning("Post-query enrichment failed for result %s: %s", result_id, exc)
