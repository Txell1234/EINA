"""Parse, persist and expose scenario milestones (temporal sequence / signposts)."""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import ScenarioMilestone

logger = logging.getLogger(__name__)

_HORIZON_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bany\s*1\b|\b1r\s+any\b|\bprimer\s+any\b", re.I), 12, "Any 1"),
    (re.compile(r"\banys?\s*2[\-–]3\b|\b2n\s+any\b", re.I), 30, "Anys 2–3"),
    (re.compile(r"\banys?\s*4[\-–]5\b|\b4t\s+any\b", re.I), 48, "Anys 4–5"),
    (re.compile(r"\b6\s*mesos\b|\b6m\b", re.I), 6, "6 mesos"),
    (re.compile(r"\b12\s*mesos\b|\b12m\b|\b1\s+any\b", re.I), 12, "12 mesos"),
    (re.compile(r"\b18\s*mesos\b|\b18m\b", re.I), 18, "18 mesos"),
]

_REVERSIBILITY_LOW = re.compile(
    r"irreversible|punt de no retorn|no retorn|permanent|estructural|constitucional|trencament",
    re.I,
)
_REVERSIBILITY_HIGH = re.compile(
    r"reversible|temporari|epis[oò]dic|puntual|negociable|modulable",
    re.I,
)


def _infer_horizon(text: str) -> tuple[int | None, str]:
    for pattern, months, label in _HORIZON_PATTERNS:
        if pattern.search(text):
            return months, label
    return None, ""


def _infer_reversibility(text: str) -> str | None:
    if _REVERSIBILITY_LOW.search(text):
        return "low"
    if _REVERSIBILITY_HIGH.search(text):
        return "high"
    return "medium"


def parse_milestones_from_narrative(narrative: str) -> list[dict[str, Any]]:
    """Best-effort extraction of milestones from scenario narrative text."""
    if not (narrative or "").strip():
        return []

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    order = 0
    current_horizon: int | None = None
    current_label = ""

    def add_milestone(title: str, indicator: str = "", source_line: str = "") -> None:
        nonlocal order, current_horizon, current_label
        title = title.strip()
        if len(title) < 8:
            return
        key = title.lower()[:120]
        if key in seen:
            return
        seen.add(key)
        blob = f"{title} {indicator} {source_line}"
        h_months, h_label = _infer_horizon(blob)
        if h_months is None:
            h_months, h_label = current_horizon, current_label
        out.append(
            {
                "order_index": order,
                "time_label": h_label or current_label,
                "horizon_months": h_months,
                "title": title[:500],
                "trigger_indicator": (indicator or title)[:800],
                "reversibility": _infer_reversibility(blob),
            }
        )
        order += 1

    for line in narrative.splitlines():
        raw = line.strip()
        if not raw:
            continue

        h_months, h_label = _infer_horizon(raw)
        if h_months and re.match(r"^(any|anys)\s", raw, re.I):
            current_horizon = h_months
            current_label = h_label
            continue

        arrow = re.match(r"^[→\-•]\s*(.+)$", raw)
        if arrow:
            add_milestone(arrow.group(1), indicator=arrow.group(1), source_line=raw)
            continue

        if re.search(
            r"\b(indicador|alerta|senyal|trigger|umbral|llindar|milestone|hit[eo])\b",
            raw,
            re.I,
        ) and len(raw) > 15:
            add_milestone(raw, indicator=raw, source_line=raw)

    if not out:
        for ind in re.findall(r"→\s*(.+?)(?:\n|$)", narrative):
            add_milestone(ind, indicator=ind)

    return out


def milestone_to_dict(m: ScenarioMilestone) -> dict[str, Any]:
    return {
        "id": m.id,
        "scenario_id": m.scenario_id,
        "order_index": m.order_index,
        "time_label": m.time_label or "",
        "horizon_months": m.horizon_months,
        "title": m.title,
        "trigger_indicator": m.trigger_indicator or m.title,
        "reversibility": m.reversibility,
    }


async def list_milestones_for_scenario(
    db: AsyncSession, scenario_id: int
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(ScenarioMilestone)
            .where(ScenarioMilestone.scenario_id == scenario_id)
            .order_by(ScenarioMilestone.order_index, ScenarioMilestone.id)
        )
    ).scalars().all()
    return [milestone_to_dict(m) for m in rows]


async def list_milestones_for_project(
    db: AsyncSession, project_id: int
) -> dict[int, list[dict[str, Any]]]:
    from models.prospective import ProspectiveScenario

    sc_r = await db.execute(
        select(ProspectiveScenario.id).where(ProspectiveScenario.project_id == project_id)
    )
    scenario_ids = list(sc_r.scalars().all())
    if not scenario_ids:
        return {}

    rows = (
        await db.execute(
            select(ScenarioMilestone)
            .where(ScenarioMilestone.scenario_id.in_(scenario_ids))
            .order_by(ScenarioMilestone.scenario_id, ScenarioMilestone.order_index)
        )
    ).scalars().all()
    by_scenario: dict[int, list[dict[str, Any]]] = {sid: [] for sid in scenario_ids}
    for m in rows:
        by_scenario.setdefault(m.scenario_id, []).append(milestone_to_dict(m))
    return by_scenario


async def persist_milestones_for_scenario(
    db: AsyncSession,
    scenario_id: int,
    narrative: str,
    *,
    replace: bool = True,
) -> list[dict[str, Any]]:
    parsed = parse_milestones_from_narrative(narrative)
    if replace:
        await db.execute(
            delete(ScenarioMilestone).where(ScenarioMilestone.scenario_id == scenario_id)
        )
    saved: list[ScenarioMilestone] = []
    for item in parsed:
        m = ScenarioMilestone(
            scenario_id=scenario_id,
            order_index=int(item.get("order_index") or 0),
            time_label=str(item.get("time_label") or ""),
            horizon_months=item.get("horizon_months"),
            title=str(item.get("title") or "")[:500],
            trigger_indicator=str(item.get("trigger_indicator") or "")[:800],
            reversibility=item.get("reversibility"),
        )
        db.add(m)
        saved.append(m)
    if saved:
        await db.commit()
        for m in saved:
            await db.refresh(m)
    else:
        await db.commit()
    logger.info("Persisted %d milestones for scenario %s", len(saved), scenario_id)
    return [milestone_to_dict(m) for m in saved]


async def create_monitors_from_milestones(
    db: AsyncSession,
    project_id: int,
    scenario_id: int,
) -> list[dict[str, Any]]:
    """Create one OSINT monitor per persisted milestone (additive to narrative → monitors)."""
    from models.prospective import AlertMonitor
    from services.alert_monitor_service import _default_monitor_sources, _keywords

    milestones = await list_milestones_for_scenario(db, scenario_id)
    if not milestones:
        from models.prospective import ProspectiveScenario

        sc_r = await db.execute(
            select(ProspectiveScenario).where(
                ProspectiveScenario.id == scenario_id,
                ProspectiveScenario.project_id == project_id,
            )
        )
        sc = sc_r.scalar_one_or_none()
        if sc and sc.narrative:
            await persist_milestones_for_scenario(db, scenario_id, sc.narrative)
            milestones = await list_milestones_for_scenario(db, scenario_id)

    from services.alert_monitor_service import _resolve_case_id

    case_id = await _resolve_case_id(db, project_id)
    created: list[dict[str, Any]] = []

    for ms in milestones:
        indicator = str(ms.get("trigger_indicator") or ms.get("title") or "").strip()
        if len(indicator) < 8:
            continue
        kws = _keywords(indicator)
        horizon_label = None
        hm = ms.get("horizon_months")
        if hm is not None:
            if hm <= 12:
                horizon_label = "3m" if hm <= 6 else "12m"
            elif hm <= 18:
                horizon_label = "6m"
            else:
                horizon_label = "18m"

        db.add(
            AlertMonitor(
                project_id=project_id,
                scenario_id=scenario_id,
                case_id=case_id,
                indicator=indicator[:500],
                keywords=kws,
                osint_sources=_default_monitor_sources(),
                is_active=1,
                lookback_days=int(hm) if hm else None,
                horizon_label=horizon_label,
            )
        )
        created.append(
            {
                "indicator": indicator,
                "keywords": kws,
                "milestone_id": ms.get("id"),
                "horizon_months": hm,
            }
        )

    await db.commit()
    return created
