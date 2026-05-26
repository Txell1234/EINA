"""
OSINT → extraction funnel metrics per case.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item

MIN_EXTRACT_TEXT = 80
MIN_ENRICH_TEXT = 200


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "unknown"
    except Exception:
        return "unknown"


def _parse_data(raw: Any) -> dict[str, Any] | None:
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _collect_articles_from_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    if osint_has_error(data):
        return []
    return flatten_osint_items(data)


async def collect_case_articles(db: AsyncSession, case_id: int) -> list[dict[str, Any]]:
    """All normalized articles linked to a case via OSINT results."""
    rows = await db.execute(
        select(OSINTResult.data, OSINTQuery.query_type)
        .join(OSINTQuery, OSINTQuery.id == OSINTResult.query_id)
        .where(OSINTQuery.case_id == case_id, OSINTResult.status == "completed")
    )
    articles: list[dict[str, Any]] = []
    for data_raw, qtype in rows.all():
        data = _parse_data(data_raw)
        if not data:
            continue
        for art in _collect_articles_from_data(data):
            merged = {**art, "query_type": qtype}
            articles.append(merged)
    return articles


def _article_stats(articles: list[dict[str, Any]], extracted_urls: set[str]) -> dict[str, Any]:
    by_url: dict[str, dict[str, Any]] = {}
    for art in articles:
        url = str(art.get("url") or "").strip()
        key = url or f"title:{art.get('title', '')[:80]}"
        if key in by_url:
            continue
        text_len = len(text_from_osint_item(art).strip())
        enriched = bool(art.get("enriched"))
        by_url[key] = {
            "url": url,
            "title": str(art.get("title") or "")[:120],
            "source": str(art.get("source") or art.get("query_type") or ""),
            "text_len": text_len,
            "enriched": enriched,
            "extractable": text_len >= MIN_EXTRACT_TEXT or bool(url),
            "needs_enrichment": bool(url) and text_len < MIN_ENRICH_TEXT,
            "extracted": bool(url and url in extracted_urls),
            "frontpage_score": float(
                art.get("frontpage_score") or art.get("importance_score") or 0
            ),
        }

    unique = list(by_url.values())
    pending = [
        a for a in unique
        if a["extractable"] and not a["extracted"] and (a["text_len"] >= MIN_EXTRACT_TEXT or a["url"])
    ]
    thin_pending = [a for a in pending if a["needs_enrichment"]]

    domains = Counter(_domain(a["url"]) for a in unique if a["url"])
    return {
        "articles_total": len(unique),
        "extractable": sum(1 for a in unique if a["extractable"]),
        "enriched": sum(1 for a in unique if a["enriched"]),
        "needs_enrichment": sum(1 for a in unique if a["needs_enrichment"]),
        "extracted_urls": sum(1 for a in unique if a["extracted"]),
        "pending_extraction": len(pending),
        "pending_thin": len(thin_pending),
        "top_domains": [{"domain": d, "count": c} for d, c in domains.most_common(8)],
        "pending_samples": sorted(pending, key=lambda x: (-x["frontpage_score"], -x["text_len"]))[:12],
    }


async def get_extraction_coverage(db: AsyncSession, case_id: int) -> dict[str, Any]:
    """Full funnel metrics for UI dashboard."""
    from models.prospective import AlertMatch

    articles = await collect_case_articles(db, case_id)

    ext_r = await db.execute(
        select(ExtractedStatement.source_url, ExtractedStatement.cleanup_decision)
        .where(ExtractedStatement.case_id == case_id)
    )
    extracted_urls: set[str] = set()
    by_decision: Counter[str] = Counter()
    for url, decision in ext_r.all():
        if url:
            extracted_urls.add(url)
        by_decision[str(decision or "UNKNOWN")] += 1

    stats = _article_stats(articles, extracted_urls)

    q_r = await db.execute(
        select(OSINTQuery.query_type, OSINTQuery.status, func.count())
        .where(OSINTQuery.case_id == case_id)
        .group_by(OSINTQuery.query_type, OSINTQuery.status)
    )
    queries_by_type = [
        {"query_type": row[0], "status": row[1], "count": row[2]}
        for row in q_r.all()
    ]

    err_r = await db.execute(
        select(func.count())
        .select_from(OSINTResult)
        .join(OSINTQuery, OSINTQuery.id == OSINTResult.query_id)
        .where(OSINTQuery.case_id == case_id, OSINTResult.status == "error")
    )
    osint_errors = err_r.scalar() or 0

    orphan_r = await db.execute(
        select(func.count()).select_from(OSINTQuery).where(OSINTQuery.case_id.is_(None))
    )
    orphan_queries = orphan_r.scalar() or 0

    alert_r = await db.execute(
        select(AlertMatch.status, func.count())
        .where(AlertMatch.case_id == case_id)
        .group_by(AlertMatch.status)
    )
    alerts_by_status = {row[0]: row[1] for row in alert_r.all()}

    short_alert_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(
            AlertMatch.case_id == case_id,
            func.length(func.coalesce(AlertMatch.excerpt, "")) < MIN_ENRICH_TEXT,
        )
    )
    alerts_short_excerpt = short_alert_r.scalar() or 0

    not_ext_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(
            AlertMatch.case_id == case_id,
            AlertMatch.extracted_statement_id.is_(None),
            AlertMatch.status.in_(["new", "reviewed"]),
        )
    )
    alerts_pending_extract = not_ext_r.scalar() or 0

    coverage_pct = 0.0
    if stats["extractable"] > 0:
        coverage_pct = round(100.0 * stats["extracted_urls"] / stats["extractable"], 1)

    return {
        "case_id": case_id,
        "coverage_percent": coverage_pct,
        "articles": stats,
        "statements": {
            "total": sum(by_decision.values()),
            "by_decision": dict(by_decision),
        },
        "osint": {
            "queries_by_type": queries_by_type,
            "error_results": osint_errors,
            "orphan_queries_global": orphan_queries,
        },
        "alerts": {
            "by_status": alerts_by_status,
            "short_excerpt": alerts_short_excerpt,
            "pending_extraction": alerts_pending_extract,
        },
        "recommendations": _build_recommendations(stats, orphan_queries, osint_errors, alerts_short_excerpt),
    }


def _build_recommendations(
    stats: dict[str, Any],
    orphan_queries: int,
    osint_errors: int,
    alerts_short: int,
) -> list[str]:
    recs: list[str] = []
    if stats["pending_extraction"] > 0:
        recs.append(
            f"Hi ha {stats['pending_extraction']} articles pendents d'extracció — executa «Extreure tot el pendent»."
        )
    if stats["pending_thin"] > 0:
        recs.append(
            f"{stats['pending_thin']} articles tenen text curt (<{MIN_ENRICH_TEXT} chars) — l'enriqueixement automàtic intentarà obtenir el cos complet."
        )
    if orphan_queries > 0:
        recs.append(
            f"{orphan_queries} consultes OSINT sense cas assignat — usa «Reparar consultes orfes»."
        )
    if osint_errors > 0:
        recs.append("Algunes consultes OSINT han fallat (GDELT 429, RSS, claus API). Revisa Integracions.")
    if alerts_short > 0:
        recs.append(
            f"{alerts_short} alertes amb excerpt curt — enriqueix abans d'extreure declaracions."
        )
    if not recs:
        recs.append("Cobertura acceptable. Revisa declaracions NEEDS_REVIEW abans d'exportar.")
    return recs
