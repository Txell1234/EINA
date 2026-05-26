"""Actor network and typology aggregation from extracted statements — additive layer."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.prospective import ProspectiveProject, ProspectiveScenario
from schemas.actor_typology import (
    SCENARIO_PROFILES,
    build_analytical_profile,
    classify_signal_type,
    infer_institution_subtype,
    normalize_actor_class,
)
from services.actor_impact_utils import canonical_actor
from services.case_topic_relevance import build_case_topic_profile


class ActorNetworkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_network(self, case_id: int) -> dict[str, Any]:
        from models.case import Case

        case_r = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_r.scalar_one_or_none()
        if not case:
            return {"case_id": case_id, "found": False, "actors": [], "edges": []}

        profile = build_case_topic_profile(case.name or "", case.description or "")
        analytical = build_analytical_profile(
            case_type=case.case_type.value if case.case_type else "general",
            themes=profile.themes,
        )

        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        )
        statements = list(stmts_r.scalars().all())

        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str], dict[str, Any]] = {}
        by_class: dict[str, int] = defaultdict(int)
        by_institution: dict[str, int] = defaultdict(int)
        by_theme: dict[str, int] = defaultdict(int)
        by_signal: dict[str, int] = defaultdict(int)

        def ensure_node(name: str, actor_type: str, institution_subtype: str | None) -> dict[str, Any]:
            key = canonical_actor(name)
            if not key:
                return {}
            if key not in nodes:
                nodes[key] = {
                    "id": key,
                    "name": key,
                    "actor_class": normalize_actor_class(actor_type),
                    "institution_subtype": institution_subtype or infer_institution_subtype(key, actor_type),
                    "statement_count": 0,
                    "avg_posture": 0.0,
                    "posture_sum": 0.0,
                    "posture_count": 0,
                    "topics": defaultdict(int),
                    "targets": set(),
                    "signal_types": defaultdict(int),
                }
            return nodes[key]

        for s in statements:
            inst_sub = getattr(s, "institution_subtype", None) or infer_institution_subtype(
                s.actor, s.actor_type
            )
            sig = getattr(s, "signal_type", None) or classify_signal_type(
                s.statement or "", s.topic or "", s.actor_type or ""
            )
            node = ensure_node(s.actor, s.actor_type or "state", inst_sub)
            if not node:
                continue
            node["statement_count"] += 1
            node["posture_sum"] += float(s.posture_value or 0)
            node["posture_count"] += 1
            if s.topic:
                node["topics"][s.topic] += 1
                by_theme[s.topic] += 1
            if sig:
                node["signal_types"][sig] += 1
                by_signal[sig] += 1
            by_class[node["actor_class"]] += 1
            by_institution[node["institution_subtype"]] += 1

            if s.posture_toward:
                target = canonical_actor(s.posture_toward)
                if target:
                    node["targets"].add(target)
                    ensure_node(target, "entity", None)
                    edge_key = (node["id"], target)
                    if edge_key not in edges:
                        edges[edge_key] = {
                            "source": node["id"],
                            "target": target,
                            "posture_sum": 0.0,
                            "count": 0,
                            "topics": set(),
                        }
                    edges[edge_key]["posture_sum"] += float(s.posture_value or 0)
                    edges[edge_key]["count"] += 1
                    if s.topic:
                        edges[edge_key]["topics"].add(s.topic)

        actor_list: list[dict[str, Any]] = []
        for node in nodes.values():
            if node["posture_count"]:
                node["avg_posture"] = round(node["posture_sum"] / node["posture_count"], 2)
            topics = dict(node.pop("topics"))
            node["topics"] = sorted(topics.items(), key=lambda x: -x[1])[:8]
            node["targets"] = sorted(node.pop("targets"))
            node["signal_types"] = dict(node.pop("signal_types"))
            actor_list.append(node)

        actor_list.sort(key=lambda x: (-x["statement_count"], x["name"]))

        edge_list = []
        for e in edges.values():
            e["avg_posture"] = round(e["posture_sum"] / max(e["count"], 1), 2)
            e["topics"] = sorted(e.pop("topics"))
            edge_list.append(e)

        scenarios = await self._load_scenarios(case_id)
        scenario_summary = []
        from services.scenario_milestone_service import list_milestones_for_scenario

        for sc in scenarios:
            profile = SCENARIO_PROFILES.get((sc.scenario_type or "").lower(), {})
            ms = await list_milestones_for_scenario(self.db, sc.id) if sc.id else []
            scenario_summary.append(
                {
                    "scenario_type": sc.scenario_type,
                    "name": sc.name,
                    "probability": sc.probability,
                    **profile,
                    "milestone_count": len(ms),
                }
            )

        return {
            "case_id": case_id,
            "found": True,
            "focus_label": profile.focus_label,
            "themes": sorted(profile.themes),
            "analytical_profile": analytical.model_dump(),
            "summary": {
                "actor_count": len(actor_list),
                "edge_count": len(edge_list),
                "by_actor_class": dict(by_class),
                "by_institution_subtype": dict(by_institution),
                "by_topic": dict(by_theme),
                "by_signal_type": dict(by_signal),
            },
            "actors": actor_list,
            "edges": edge_list,
            "scenarios": scenario_summary,
        }

    async def _load_scenarios(self, case_id: int) -> list[ProspectiveScenario]:
        proj_r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        project = proj_r.scalar_one_or_none()
        if not project:
            return []
        sc_r = await self.db.execute(
            select(ProspectiveScenario).where(ProspectiveScenario.project_id == project.id)
        )
        return list(sc_r.scalars().all())
