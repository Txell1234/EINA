"""
Source provenance — OSINT query → article → statement → claim / alert match.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url or "").netloc.replace("www.", "") or "desconegut"
    except Exception:
        return "desconegut"


async def statement_provenance(db: AsyncSession, statement_id: int) -> dict[str, Any]:
    r = await db.execute(select(ExtractedStatement).where(ExtractedStatement.id == statement_id))
    stmt = r.scalar_one_or_none()
    if not stmt:
        raise LookupError("Declaració no trobada")

    osint_query = None
    osint_result = None
    if stmt.osint_result_id:
        res_r = await db.execute(
            select(OSINTResult, OSINTQuery)
            .join(OSINTQuery, OSINTResult.query_id == OSINTQuery.id)
            .where(OSINTResult.id == stmt.osint_result_id)
        )
        row = res_r.first()
        if row:
            osint_result, osint_query = row

    chain: list[dict[str, Any]] = []
    if osint_query:
        chain.append({
            "step": "osint_query",
            "label": "Consulta OSINT",
            "detail": osint_query.query_type,
            "meta": {
                "query_id": osint_query.id,
                "query_type": osint_query.query_type,
                "query_params": osint_query.query_params or {},
                "created_at": osint_query.created_at.isoformat() if osint_query.created_at else None,
            },
        })
    if osint_result:
        chain.append({
            "step": "osint_result",
            "label": "Resultat OSINT",
            "detail": f"Resultat #{osint_result.id}",
            "meta": {"result_id": osint_result.id, "status": osint_result.status},
        })

    chain.append({
        "step": "article",
        "label": "Article font",
        "detail": stmt.source_url or "Sense URL",
        "meta": {
            "url": stmt.source_url,
            "date": stmt.source_date,
            "domain": _domain_from_url(stmt.source_url or ""),
            "excerpt": (stmt.source_text_excerpt or "")[:500],
        },
    })
    chain.append({
        "step": "statement",
        "label": "Declaració extreta",
        "detail": (stmt.statement or "")[:120],
        "meta": {
            "statement_id": stmt.id,
            "actor": stmt.actor,
            "posture_value": stmt.posture_value,
            "grounding_score": stmt.grounding_score,
            "cleanup_decision": stmt.cleanup_decision,
        },
    })

    return {
        "statement_id": stmt.id,
        "case_id": stmt.case_id,
        "has_source_url": bool((stmt.source_url or "").startswith("http")),
        "chain": chain,
    }


async def match_provenance(db: AsyncSession, match_id: int) -> dict[str, Any]:
    from models.prospective import AlertMatch, AlertMonitor, ProspectiveScenario

    r = await db.execute(
        select(AlertMatch, AlertMonitor, ProspectiveScenario)
        .join(AlertMonitor, AlertMatch.monitor_id == AlertMonitor.id)
        .outerjoin(ProspectiveScenario, AlertMatch.scenario_id == ProspectiveScenario.id)
        .where(AlertMatch.id == match_id)
    )
    row = r.first()
    if not row:
        raise LookupError("Coincidència no trobada")
    match, monitor, scenario = row

    chain: list[dict[str, Any]] = []
    if scenario:
        chain.append({
            "step": "scenario",
            "label": "Escenari prospectiu",
            "detail": scenario.name,
            "meta": {"scenario_id": scenario.id},
        })
    chain.append({
        "step": "monitor",
        "label": "Indicador d'alerta",
        "detail": monitor.indicator,
        "meta": {"monitor_id": monitor.id, "keywords": monitor.keywords or []},
    })
    if match.osint_query_id:
        q_r = await db.execute(select(OSINTQuery).where(OSINTQuery.id == match.osint_query_id))
        oq = q_r.scalar_one_or_none()
        if oq:
            chain.append({
                "step": "osint_query",
                "label": "Consulta OSINT",
                "detail": oq.query_type,
                "meta": {
                    "query_id": oq.id,
                    "query_type": oq.query_type,
                    "query_params": oq.query_params or {},
                },
            })
    chain.append({
        "step": "article",
        "label": "Article detectat",
        "detail": match.title or match.url or "—",
        "meta": {
            "url": match.url,
            "date": match.published_at,
            "source_type": match.source_type,
            "excerpt": match.excerpt,
            "matched_keywords": match.matched_keywords or [],
            "match_score": match.match_score,
        },
    })
    if match.extracted_statement_id:
        chain.append({
            "step": "statement",
            "label": "Extret al cas",
            "detail": f"Declaració #{match.extracted_statement_id}",
            "meta": {"extracted_statement_id": match.extracted_statement_id},
        })

    return {
        "match_id": match.id,
        "case_id": match.case_id,
        "has_source_url": bool((match.url or "").startswith("http")),
        "chain": chain,
    }


async def export_readiness(db: AsyncSession, case_id: int) -> dict[str, Any]:
    """Pre-export traceability check for a case."""
    from models.prospective import AlertMatch
    from services.actor_impact_service import ActorImpactService
    from services.extract_service import ExtractService

    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    extract_svc = ExtractService(db)
    validation = await extract_svc.validate_case(case_id)
    if validation.get("has_data"):
        for fg in validation.get("flagged_grounding") or []:
            warnings.append({
                "type": "low_grounding",
                "id": fg.get("id"),
                "message": f"Grounding baix ({fg.get('score')}) — {fg.get('actor')}",
                "source_url": fg.get("source_url"),
            })
        no_url_r = await db.execute(
            select(func.count())
            .select_from(ExtractedStatement)
            .where(
                ExtractedStatement.case_id == case_id,
                (ExtractedStatement.source_url == "") | (ExtractedStatement.source_url.is_(None)),
            )
        )
        no_url = no_url_r.scalar() or 0
        if no_url:
            warnings.append({
                "type": "statements_without_url",
                "count": no_url,
                "message": f"{no_url} declaració(ns) sense URL de font",
            })

    try:
        impact = await ActorImpactService(db).get_latest(case_id)
        if impact and impact.get("validation"):
            v = impact["validation"]
            if not v.get("export_ready"):
                n = v.get("claims_without_citation", 0)
                issues.append({
                    "type": "claims_without_citation",
                    "count": n,
                    "message": f"{n} conclusió(ns) d'impacte sense citació verificable",
                })
    except Exception:
        pass

    alert_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(
            AlertMatch.case_id == case_id,
            AlertMatch.status.in_(["new", "reviewed", "actioned"]),
            (AlertMatch.url == "") | (AlertMatch.url.is_(None)),
        )
    )
    alerts_no_url = alert_r.scalar() or 0
    if alerts_no_url:
        warnings.append({
            "type": "alerts_without_url",
            "count": alerts_no_url,
            "message": f"{alerts_no_url} alerta(es) sense URL",
        })

    decision_annex_hint: dict[str, Any] = {}
    milestone_count = 0
    signal_breakdown: dict[str, int] = {}
    try:
        from models.prospective import ProspectiveProject, ProspectiveScenario, ScenarioMilestone
        from services.decision_annex_service import build_decision_annex

        proj_r = await db.execute(
            select(ProspectiveProject.id)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        project_id = proj_r.scalar_one_or_none()
        if project_id:
            ms_r = await db.execute(
                select(func.count())
                .select_from(ScenarioMilestone)
                .join(ProspectiveScenario, ScenarioMilestone.scenario_id == ProspectiveScenario.id)
                .where(ProspectiveScenario.project_id == project_id)
            )
            milestone_count = int(ms_r.scalar() or 0)
            annex = await build_decision_annex(db, case_id, project_id=project_id)
            if annex.get("has_content"):
                decision_annex_hint = {
                    "available": True,
                    "points_of_no_return": len(annex.get("points_of_no_return") or []),
                    "key_actors": len(annex.get("key_actors") or []),
                    "signal_breakdown": annex.get("signal_breakdown") or {},
                }
                signal_breakdown = annex.get("signal_breakdown") or {}
    except Exception:
        pass

    export_ready = len(issues) == 0
    return {
        "case_id": case_id,
        "export_ready": export_ready,
        "can_export_with_warning": True,
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings[:30],
        "validation_summary": {
            "total_statements": validation.get("total_statements", 0),
            "below_threshold": validation.get("below_threshold", 0),
            "flagged_grounding": validation.get("flagged_grounding", [])[:10],
        },
        "decision_annex_available": bool(decision_annex_hint.get("available")),
        "decision_annex_hint": decision_annex_hint,
        "milestone_count": milestone_count,
        "signal_breakdown": signal_breakdown,
    }
