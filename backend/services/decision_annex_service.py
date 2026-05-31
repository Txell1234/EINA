"""
Decision annex and weekly INTSUM digest — additive layer for reports and dashboards.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.prospective import (
    AlertMatch,
    AlertMonitor,
    ProspectiveProject,
    ProspectiveScenario,
    ScenarioMilestone,
)
from schemas.actor_typology import classify_signal_type
from services.actor_network_service import ActorNetworkService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cutoff_naive(days: int) -> datetime:
    """Naive UTC cutoff for reliable SQLite datetime comparisons."""
    return (_utc_now() - timedelta(days=days)).replace(tzinfo=None)


def _stmt_payload(s: ExtractedStatement) -> dict[str, Any]:
    return {
        "id": s.id,
        "actor": s.actor,
        "statement": (s.statement or "")[:240],
        "posture_value": s.posture_value,
        "topic": s.topic,
        "signal_type": getattr(s, "signal_type", None),
        "extracted_at": s.extracted_at.isoformat() if s.extracted_at else None,
    }


def _posture_highlights_from_network(net: dict[str, Any]) -> list[dict[str, Any]]:
    actors = net.get("actors") or []
    if not actors:
        return []
    ranked = sorted(
        actors,
        key=lambda a: abs(float(a.get("avg_posture") or 0)),
        reverse=True,
    )
    strong = [
        {
            "actor": a.get("name"),
            "avg_posture": a.get("avg_posture"),
            "statement_count": a.get("statement_count"),
            "highlight_type": "posture",
        }
        for a in ranked[:5]
        if abs(float(a.get("avg_posture") or 0)) >= 0.5
    ]
    if strong:
        return strong
    by_volume = sorted(actors, key=lambda a: -(a.get("statement_count") or 0))
    return [
        {
            "actor": a.get("name"),
            "avg_posture": a.get("avg_posture"),
            "statement_count": a.get("statement_count"),
            "highlight_type": "top_activity",
        }
        for a in by_volume[:3]
        if (a.get("statement_count") or 0) > 0
    ]


async def build_decision_annex(
    db: AsyncSession,
    case_id: int,
    *,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Structured decision annex; empty sections omitted at render time."""
    horizons: list[dict[str, Any]] = []
    no_return_points: list[dict[str, Any]] = []
    key_actors: list[dict[str, Any]] = []
    signal_breakdown: dict[str, int] = {"structural": 0, "episodic": 0, "unknown": 0}

    if project_id:
        ms_r = await db.execute(
            select(ScenarioMilestone)
            .join(ProspectiveScenario, ScenarioMilestone.scenario_id == ProspectiveScenario.id)
            .where(ProspectiveScenario.project_id == project_id)
            .order_by(ScenarioMilestone.order_index)
        )
        for ms in ms_r.scalars().all():
            label = ms.time_label or (f"{ms.horizon_months}m" if ms.horizon_months else "")
            if label or ms.horizon_months:
                horizons.append(
                    {
                        "label": label,
                        "title": ms.title,
                        "scenario_id": ms.scenario_id,
                        "reversibility": ms.reversibility,
                    }
                )
            if (ms.reversibility or "").lower() == "low":
                no_return_points.append(
                    {
                        "title": ms.title,
                        "trigger": ms.trigger_indicator,
                        "horizon": ms.time_label or (f"{ms.horizon_months}m" if ms.horizon_months else ""),
                    }
                )

    net_svc = ActorNetworkService(db)
    network = await net_svc.build_network(case_id)
    if network.get("found"):
        for actor in (network.get("actors") or [])[:10]:
            key_actors.append(
                {
                    "name": actor.get("name"),
                    "actor_class": actor.get("actor_class"),
                    "institution_subtype": actor.get("institution_subtype"),
                    "statement_count": actor.get("statement_count", 0),
                    "avg_posture": actor.get("avg_posture", 0),
                    "top_topics": [t[0] for t in (actor.get("topics") or [])[:3]],
                }
            )
        summary = network.get("summary") or {}
        by_signal = summary.get("by_signal_type") or {}
        for sig, count in by_signal.items():
            key = (sig or "unknown").lower()
            if key in signal_breakdown:
                signal_breakdown[key] += int(count)
            else:
                signal_breakdown["unknown"] += int(count)

    if not any(signal_breakdown.values()):
        stmts_r = await db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        )
        for s in stmts_r.scalars().all():
            sig = getattr(s, "signal_type", None) or classify_signal_type(
                s.statement or "", s.topic or "", s.actor_type or ""
            )
            key = (sig or "unknown").lower()
            if key in signal_breakdown:
                signal_breakdown[key] += 1
            else:
                signal_breakdown["unknown"] += 1

    monitor_horizons: list[str] = []
    if project_id:
        mon_r = await db.execute(
            select(AlertMonitor.horizon_label)
            .where(AlertMonitor.project_id == project_id)
            .where(AlertMonitor.horizon_label.isnot(None))
        )
        monitor_horizons = sorted({h for (h,) in mon_r.all() if h})

    has_content = bool(
        horizons
        or no_return_points
        or key_actors
        or any(signal_breakdown.values())
        or monitor_horizons
    )

    return {
        "case_id": case_id,
        "project_id": project_id,
        "has_content": has_content,
        "horizons": horizons,
        "monitor_horizons": monitor_horizons,
        "points_of_no_return": no_return_points,
        "key_actors": key_actors,
        "signal_breakdown": signal_breakdown,
        "scenario_profiles": network.get("scenarios") or [],
    }


def decision_annex_html(annex: dict[str, Any]) -> str:
    """Render decision annex as HTML fragment (no outer html/body)."""
    if not annex.get("has_content"):
        return ""

    parts: list[str] = [
        "<h1>Annex de decisió (intel·ligència aplicada)</h1>",
        "<p class='muted'>Secció opt-in: horitzons, punts de no retorn, actors clau i senyals estructurals vs episòdics.</p>",
    ]

    monitor_h = annex.get("monitor_horizons") or []
    horizons = annex.get("horizons") or []
    if monitor_h or horizons:
        parts.append("<h2>Horitzons de vigilància</h2>")
        if monitor_h:
            parts.append(f"<p><strong>Monitors configurats:</strong> {html_escape(', '.join(monitor_h))}</p>")
        if horizons:
            parts.append('<table class="grid"><thead><tr><th>Horitzó</th><th>Hito</th><th>Reversibilitat</th></tr></thead><tbody>')
            for h in horizons[:20]:
                parts.append(
                    f"<tr><td>{html_escape(str(h.get('label', '')))}</td>"
                    f"<td>{html_escape(str(h.get('title', '')))}</td>"
                    f"<td>{html_escape(str(h.get('reversibility', '')))}</td></tr>"
                )
            parts.append("</tbody></table>")

    pnr = annex.get("points_of_no_return") or []
    if pnr:
        parts.append("<h2>Punts de no retorn (baixa reversibilitat)</h2><ul>")
        for p in pnr[:15]:
            parts.append(
                f"<li><strong>{html_escape(str(p.get('title', '')))}</strong>"
                f" — {html_escape(str(p.get('trigger', '')))}"
                f" <span class='muted'>({html_escape(str(p.get('horizon', '')))})</span></li>"
            )
        parts.append("</ul>")

    actors = annex.get("key_actors") or []
    if actors:
        parts.append("<h2>Actors clau (xarxa OSINT)</h2>")
        parts.append(
            '<table class="grid"><thead><tr>'
            "<th>Actor</th><th>Classe</th><th>Declaracions</th><th>Postura mitjana</th><th>Temes</th>"
            "</tr></thead><tbody>"
        )
        for a in actors:
            topics = ", ".join(a.get("top_topics") or [])
            parts.append(
                f"<tr><td>{html_escape(str(a.get('name', '')))}</td>"
                f"<td>{html_escape(str(a.get('actor_class', '')))}</td>"
                f"<td>{a.get('statement_count', 0)}</td>"
                f"<td>{a.get('avg_posture', 0)}</td>"
                f"<td>{html_escape(topics)}</td></tr>"
            )
        parts.append("</tbody></table>")

    sig = annex.get("signal_breakdown") or {}
    total_sig = sum(sig.values())
    if total_sig:
        parts.append("<h2>Estructural vs episòdic</h2>")
        parts.append(
            f"<p>Estructural: <strong>{sig.get('structural', 0)}</strong> · "
            f"Episòdic: <strong>{sig.get('episodic', 0)}</strong> · "
            f"Sense classificar: <strong>{sig.get('unknown', 0)}</strong></p>"
        )

    profiles = annex.get("scenario_profiles") or []
    if profiles:
        parts.append("<h2>Perfils d'escenari (Godet)</h2><ul>")
        for sc in profiles[:6]:
            parts.append(
                f"<li>{html_escape(str(sc.get('name', '')))} "
                f"({html_escape(str(sc.get('scenario_type', '')))}) — "
                f"{sc.get('milestone_count', 0)} milestone(s)</li>"
            )
        parts.append("</ul>")

    return "".join(parts)


async def build_case_intsum(db: AsyncSession, case_id: int, *, days: int = 7) -> dict[str, Any]:
    """Weekly-style intelligence summary for a case (does not replace dashboard)."""
    days = max(1, min(days, 90))
    cutoff = _cutoff_naive(days)
    period_end = _utc_now()

    from models.case import Case

    case_r = await db.execute(select(Case).where(Case.id == case_id))
    case = case_r.scalar_one_or_none()
    if not case:
        return {"case_id": case_id, "found": False, "days": days}

    def _alert_row(match: AlertMatch, monitor: AlertMonitor) -> dict[str, Any]:
        return {
            "id": match.id,
            "title": match.title,
            "url": match.url,
            "monitor": monitor.indicator,
            "horizon_label": monitor.horizon_label,
            "match_score": match.match_score,
            "matched_keywords": match.matched_keywords or [],
            "first_seen_at": match.first_seen_at.isoformat() if match.first_seen_at else None,
            "status": match.status,
        }

    alerts_in_window_r = await db.execute(
        select(AlertMatch, AlertMonitor)
        .join(AlertMonitor, AlertMatch.monitor_id == AlertMonitor.id)
        .where(AlertMatch.case_id == case_id)
        .where(AlertMatch.first_seen_at >= cutoff)
        .order_by(AlertMatch.first_seen_at.desc())
        .limit(50)
    )
    alerts_in_window_rows = alerts_in_window_r.all()
    alert_items = [_alert_row(m, mon) for m, mon in alerts_in_window_rows]
    alerts_in_window_count = len(alerts_in_window_rows)
    alerts_fallback = False
    if not alert_items:
        alerts_recent_r = await db.execute(
            select(AlertMatch, AlertMonitor)
            .join(AlertMonitor, AlertMatch.monitor_id == AlertMonitor.id)
            .where(AlertMatch.case_id == case_id)
            .order_by(AlertMatch.first_seen_at.desc())
            .limit(8)
        )
        alert_items = [_alert_row(m, mon) for m, mon in alerts_recent_r.all()]
        alerts_fallback = bool(alert_items)

    stmts_window_r = await db.execute(
        select(ExtractedStatement)
        .where(ExtractedStatement.case_id == case_id)
        .where(ExtractedStatement.extracted_at >= cutoff)
        .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        .order_by(ExtractedStatement.extracted_at.desc())
        .limit(40)
    )
    statements_in_window = list(stmts_window_r.scalars().all())
    stmt_items = [_stmt_payload(s) for s in statements_in_window]
    statements_fallback = False
    if not stmt_items:
        stmts_recent_r = await db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
            .order_by(ExtractedStatement.extracted_at.desc())
            .limit(8)
        )
        stmt_items = [_stmt_payload(s) for s in stmts_recent_r.scalars().all()]
        statements_fallback = bool(stmt_items)

    net = await ActorNetworkService(db).build_network(case_id)
    posture_highlights = _posture_highlights_from_network(net) if net.get("found") else []

    proj_r = await db.execute(
        select(ProspectiveProject.id)
        .where(ProspectiveProject.case_id == case_id)
        .order_by(ProspectiveProject.created_at.desc())
        .limit(1)
    )
    project_id = proj_r.scalar_one_or_none()
    milestone_count = 0
    if project_id:
        ms_r = await db.execute(
            select(ScenarioMilestone.id)
            .join(ProspectiveScenario, ScenarioMilestone.scenario_id == ProspectiveScenario.id)
            .where(ProspectiveScenario.project_id == project_id)
        )
        milestone_count = len(ms_r.all())

    signal_breakdown = (net.get("summary") or {}).get("by_signal_type") or {}
    new_statements_in_window = len(statements_in_window)

    has_activity = bool(
        alert_items
        or stmt_items
        or posture_highlights
        or milestone_count
        or any(signal_breakdown.values())
    )

    return {
        "case_id": case_id,
        "found": True,
        "case_name": case.name,
        "days": days,
        "period_start": cutoff.isoformat(),
        "period_end": period_end.isoformat(),
        "has_activity": has_activity,
        "summary": {
            "alert_matches": alerts_in_window_count,
            "new_statements": new_statements_in_window,
            "posture_highlights": len(posture_highlights),
            "milestone_count": milestone_count,
            "alerts_shown": len(alert_items),
            "statements_shown": len(stmt_items),
            "alerts_fallback": alerts_fallback,
            "statements_fallback": statements_fallback,
        },
        "alerts": alert_items,
        "statements": stmt_items,
        "posture_highlights": posture_highlights,
        "signal_breakdown": signal_breakdown,
    }
