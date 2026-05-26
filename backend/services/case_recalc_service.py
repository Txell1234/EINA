"""Detect stale actor-impact data and trigger structured recalculation."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.actor_impact import ActorImpactAssessment
from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult
from models.prospective import AlertMatch

logger = logging.getLogger(__name__)


async def collect_input_counts(db: AsyncSession, case_id: int) -> dict[str, int]:
    stmt_count = (
        await db.execute(
            select(func.count())
            .select_from(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
        )
    ).scalar() or 0

    alert_count = (
        await db.execute(
            select(func.count())
            .select_from(AlertMatch)
            .where(AlertMatch.case_id == case_id)
        )
    ).scalar() or 0

    queries_r = await db.execute(select(OSINTQuery).where(OSINTQuery.case_id == case_id))
    queries = list(queries_r.scalars().all())
    osint_results = 0
    tavily_research = 0
    for q in queries:
        results_r = await db.execute(select(OSINTResult).where(OSINTResult.query_id == q.id))
        for r in results_r.scalars().all():
            osint_results += 1
            if q.query_type in ("tavily_research", "tavily_research_get"):
                data = r.data if isinstance(r.data, dict) else {}
                if data.get("research_report"):
                    tavily_research += 1

    return {
        "statements": int(stmt_count),
        "alert_matches": int(alert_count),
        "osint_results": int(osint_results),
        "tavily_research_reports": int(tavily_research),
    }


async def is_actor_impact_stale(
    db: AsyncSession,
    case_id: int,
    latest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if latest is None:
        from services.actor_impact_service import ActorImpactService

        latest = await ActorImpactService(db).get_latest(case_id)

    current = await collect_input_counts(db, case_id)
    if not latest:
        return {
            "stale": current["statements"] > 0 or current["alert_matches"] > 0,
            "reasons": ["sense_avaluació_prèvia"] if current["statements"] else [],
            "current_counts": current,
            "saved_counts": {},
            "saved_at": None,
        }

    saved = (latest.get("input_snapshot") or {}) if isinstance(latest, dict) else {}
    reasons: list[str] = []
    for key, label in (
        ("statements", "noves_declaracions"),
        ("alert_matches", "noves_alertes"),
        ("osint_results", "noves_consultes_osint"),
        ("tavily_research_reports", "nou_informe_tavily_research"),
    ):
        if current.get(key, 0) > saved.get(key, 0):
            reasons.append(label)

    return {
        "stale": bool(reasons),
        "reasons": reasons,
        "current_counts": current,
        "saved_counts": saved,
        "saved_at": latest.get("saved_at"),
    }


async def refresh_actor_impact_for_report(db: AsyncSession, case_id: int) -> dict[str, Any]:
    """Always use fresh actor impact for report export when data changed."""
    from services.actor_impact_service import ActorImpactService

    svc = ActorImpactService(db)
    freshness = await is_actor_impact_stale(db, case_id)
    if freshness["stale"]:
        logger.info("Recalculant impacte d'actors per informe (cas %s): %s", case_id, freshness["reasons"])
        data = await svc.analyze_and_save(case_id)
    else:
        data = await svc.get_latest(case_id)
        if not data:
            data = await svc.build_assessment(case_id)
    data["data_freshness"] = await is_actor_impact_stale(db, case_id, data)
    return data


async def maybe_recalc_after_data_change(
    db: AsyncSession,
    case_id: int,
    *,
    reason: str,
    min_statements: int = 1,
) -> dict[str, Any] | None:
    """Recalculate and persist actor impact after new OSINT/alerts/research."""
    counts = await collect_input_counts(db, case_id)
    if counts["statements"] < min_statements and counts["alert_matches"] == 0:
        return None
    try:
        from services.actor_impact_service import ActorImpactService

        svc = ActorImpactService(db)
        data = await svc.analyze_and_save(case_id)
        data["recalc_reason"] = reason
        data["recalc_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Impacte d'actors recalculat (cas %s, motiu=%s)", case_id, reason)
        return data
    except Exception as exc:
        logger.warning("Recàlcul d'impacte fallit (cas %s): %s", case_id, exc)
        return None


async def build_report_delta(db: AsyncSession, case_id: int, actor_impact: dict[str, Any]) -> dict[str, Any]:
    """Structured delta since last saved actor-impact snapshot."""
    freshness = actor_impact.get("data_freshness") or await is_actor_impact_stale(db, case_id, actor_impact)
    current = freshness.get("current_counts") or await collect_input_counts(db, case_id)
    saved = freshness.get("saved_counts") or (actor_impact.get("input_snapshot") or {})
    deltas = {
        k: max(0, int(current.get(k, 0)) - int(saved.get(k, 0)))
        for k in ("statements", "alert_matches", "osint_results", "tavily_research_reports")
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "has_new_data": any(deltas.values()) or freshness.get("stale"),
        "deltas": deltas,
        "current_totals": current,
        "previous_totals": saved,
        "stale_reasons": freshness.get("reasons") or [],
        "assessment_saved_at": actor_impact.get("saved_at"),
    }
