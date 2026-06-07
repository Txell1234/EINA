"""
Actor impact analysis — who is affected, under which scenario, with cited evidence.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.actor_impact import ActorImpactAssessment
from models.extract import ExtractedStatement
from models.geopolitical import DiplomaticEvent, GeopoliticalRisk
from models.prospective import (
    AlertMatch,
    AlertMonitor,
    MACTORPosture,
    MACTORResult,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
)
from services.actor_impact_utils import (
    coerce_evidence_text,
    build_osint_signals,
    canonical_actor,
    ensure_four_scenarios,
    filter_cited_evidence,
    impact_label,
    justify_scenarios,
    merge_scenario_with_justification,
    scenario_valence,
    validate_claims,
)
from services.actor_motivation_service import build_actor_motivation
from services.case_recalc_service import collect_input_counts
from services.retrospective_service import RetrospectiveService

logger = logging.getLogger(__name__)

class ActorImpactService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_project(self, case_id: int) -> ProspectiveProject | None:
        r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    def _posture_trend_for_actor(
        self, actor_name: str, actor_posture_summary: list[dict[str, Any]]
    ) -> str | None:
        for row in actor_posture_summary:
            if canonical_actor(row.get("actor", "")) == canonical_actor(actor_name):
                return row.get("trend")
        return None

    async def build_assessment(self, case_id: int, project_id: int | None = None) -> dict[str, Any]:
        project = None
        if project_id:
            r = await self.db.execute(
                select(ProspectiveProject).where(
                    ProspectiveProject.id == project_id,
                    ProspectiveProject.case_id == case_id,
                )
            )
            project = r.scalar_one_or_none()
        if not project:
            project = await self._resolve_project(case_id)

        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        )
        statements = list(stmts_r.scalars().all())

        events_r = await self.db.execute(
            select(DiplomaticEvent).where(DiplomaticEvent.case_id == case_id)
        )
        events = list(events_r.scalars().all())

        risks_r = await self.db.execute(
            select(GeopoliticalRisk).where(GeopoliticalRisk.case_id == case_id)
        )
        geo_risks = list(risks_r.scalars().all())

        alert_matches_r = await self.db.execute(
            select(AlertMatch).where(AlertMatch.case_id == case_id)
        )
        alert_matches = list(alert_matches_r.scalars().all())
        monitor_ids = {m.monitor_id for m in alert_matches if m.monitor_id}
        monitors: dict[int, AlertMonitor] = {}
        scenarios_by_id: dict[int, ProspectiveScenario] = {}
        if monitor_ids:
            mon_r = await self.db.execute(
                select(AlertMonitor).where(AlertMonitor.id.in_(monitor_ids))
            )
            monitors = {m.id: m for m in mon_r.scalars().all()}

        retro = await RetrospectiveService(self.db).build_retrospective(case_id, project.id if project else None)
        posture_summary = retro.get("actor_posture_summary") or [] if retro.get("has_data") else []

        osint_signals = build_osint_signals(statements, events, geo_risks)

        prospective_actors: list[ProspectiveActor] = []
        mactor_postures: list[MACTORPosture] = []
        scenarios: list[ProspectiveScenario] = []
        mactor_mobilisation: dict[str, float] = {}
        pid = project.id if project else None

        if project:
            pa_r = await self.db.execute(
                select(ProspectiveActor).where(ProspectiveActor.project_id == project.id)
            )
            prospective_actors = list(pa_r.scalars().all())
            mp_r = await self.db.execute(
                select(MACTORPosture).where(MACTORPosture.project_id == project.id)
            )
            mactor_postures = list(mp_r.scalars().all())
            sc_r = await self.db.execute(
                select(ProspectiveScenario).where(ProspectiveScenario.project_id == project.id)
            )
            scenarios = list(sc_r.scalars().all())
            scenarios_by_id = {s.id: s for s in scenarios if s.id}
            mr_r = await self.db.execute(
                select(MACTORResult).where(MACTORResult.project_id == project.id)
            )
            mactor_result = mr_r.scalar_one_or_none()
            if mactor_result and isinstance(mactor_result.mobilisation_actors, dict):
                for code, val in mactor_result.mobilisation_actors.items():
                    try:
                        mactor_mobilisation[str(code)] = float(val)
                    except (TypeError, ValueError):
                        continue

        actor_map: dict[str, dict[str, Any]] = {}

        def ensure_actor(name: str, source: str, actor_type: str = "state") -> dict[str, Any]:
            key = canonical_actor(name)
            if not key:
                return {}
            if key not in actor_map:
                actor_map[key] = {
                    "name": key,
                    "type": actor_type,
                    "institution_subtype": None,
                    "sources": set(),
                    "statement_count": 0,
                    "posture_sum": 0.0,
                    "posture_count": 0,
                    "topics": defaultdict(int),
                    "countries": set(),
                    "evidence": [],
                    "mactor_avg": None,
                    "geo_risk_score": None,
                }
            actor_map[key]["sources"].add(source)
            return actor_map[key]

        for s in statements:
            rec = ensure_actor(s.actor, "extraction", s.actor_type or "state")
            if not rec:
                continue
            from schemas.actor_typology import infer_institution_subtype

            inst = getattr(s, "institution_subtype", None) or infer_institution_subtype(
                s.actor, s.actor_type
            )
            if inst and not rec.get("institution_subtype"):
                rec["institution_subtype"] = inst
            rec["statement_count"] += 1
            rec["posture_sum"] += float(s.posture_value or 0)
            rec["posture_count"] += 1
            if s.topic:
                rec["topics"][s.topic] += 1
            if s.posture_toward:
                ensure_actor(s.posture_toward, "extraction_relation", "entity")
            rec["evidence"].append(
                {
                    "statement_id": s.id,
                    "source_url": s.source_url or "",
                    "source_date": s.source_date or "",
                    "excerpt": (s.statement or "")[:280],
                    "grounding_score": s.grounding_score,
                    "posture_value": s.posture_value,
                    "topic": s.topic or "",
                }
            )

        for pa in prospective_actors:
            rec = ensure_actor(pa.name, "prospective", "strategic")
            if rec:
                if pa.strategic_goals:
                    rec["strategic_goals"] = pa.strategic_goals
                rec["force_score"] = pa.force_score

        actor_code_to_name = {pa.code: pa.name for pa in prospective_actors}
        mactor_by_actor: dict[str, list[int]] = defaultdict(list)
        for mp in mactor_postures:
            name = actor_code_to_name.get(mp.actor_code or "", mp.actor_code or "")
            if name:
                mactor_by_actor[canonical_actor(name)].append(int(mp.posture_value or 0))

        for actor_name, vals in mactor_by_actor.items():
            rec = ensure_actor(actor_name, "mactor", "strategic")
            if rec and vals:
                rec["mactor_avg"] = round(sum(vals) / len(vals), 2)
                code = next((c for c, n in actor_code_to_name.items() if canonical_actor(n) == actor_name), None)
                if code and code in mactor_mobilisation:
                    rec["mactor_mobilisation"] = mactor_mobilisation[code]
                elif actor_name in mactor_mobilisation:
                    rec["mactor_mobilisation"] = mactor_mobilisation[actor_name]

        for ev in events:
            for country in ev.countries or []:
                rec = ensure_actor(str(country), "geopolitical_event", "state")
                if rec:
                    rec["countries"].add(str(country))
                    rec["evidence"].append(
                        {
                            "source_url": coerce_evidence_text(
                                (ev.source_references or [None])[0] if ev.source_references else None
                            ),
                            "source_date": ev.event_date.isoformat() if ev.event_date else "",
                            "excerpt": (ev.title or "")[:200],
                            "grounding_score": None,
                            "posture_value": ev.sentiment_score,
                            "topic": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                            "event_type": "diplomatic",
                        }
                    )

        for gr in geo_risks:
            rec = ensure_actor(gr.country, "geopolitical_risk", "state")
            if rec:
                rec["geo_risk_score"] = round(float(gr.overall_risk_score or 0), 1)
                rec["countries"].add(gr.country)

        actors_out: list[dict[str, Any]] = []
        for key, rec in sorted(actor_map.items(), key=lambda x: -x[1]["statement_count"]):
            avg_posture = (
                round(rec["posture_sum"] / rec["posture_count"], 2) if rec["posture_count"] else 0.0
            )
            top_topics = sorted(rec["topics"].items(), key=lambda x: -x[1])[:5]
            evidence = sorted(
                rec["evidence"],
                key=lambda e: abs(float(e.get("posture_value") or 0)),
                reverse=True,
            )[:8]
            trend = self._posture_trend_for_actor(key, posture_summary)
            motivation = build_actor_motivation(
                key,
                statements=statements,
                alert_matches=alert_matches,
                monitors=monitors,
                scenarios_by_id=scenarios_by_id,
                mactor_mobilisation=rec.get("mactor_mobilisation"),
                strategic_goals=rec.get("strategic_goals") or None,
            )
            actors_out.append(
                {
                    "name": rec["name"],
                    "type": rec["type"],
                    "institution_subtype": rec.get("institution_subtype"),
                    "sources": sorted(rec["sources"]),
                    "statement_count": rec["statement_count"],
                    "avg_posture": avg_posture,
                    "posture_trend": trend,
                    "mactor_avg": rec.get("mactor_avg"),
                    "mactor_mobilisation": rec.get("mactor_mobilisation"),
                    "geo_risk_score": rec.get("geo_risk_score"),
                    "topics": [t for t, _ in top_topics],
                    "countries": sorted(rec["countries"]),
                    "strategic_goals": rec.get("strategic_goals") or [],
                    "force_score": rec.get("force_score"),
                    "top_evidence": filter_cited_evidence(evidence) or evidence[:3],
                    "motivation": motivation["text"],
                    "motivation_sources": motivation["sources"],
                    "motivation_alerts": motivation["alert_signals"],
                }
            )

        scenarios = ensure_four_scenarios(scenarios)

        scenario_justifications = justify_scenarios(scenarios, osint_signals)
        justification_by_name = {j["scenario_name"]: j for j in scenario_justifications}

        scenarios_out = [
            merge_scenario_with_justification(
                sc,
                justification_by_name.get(sc.name),
            )
            for sc in scenarios
        ]

        prob_by_name = {
            s["name"]: s.get("estimated_probability_pct")
            for s in scenarios_out
            if s.get("estimated_probability_pct") is not None
        }
        for j in scenario_justifications:
            prob_by_name.setdefault(j["scenario_name"], j["estimated_probability_pct"])

        input_snapshot = await collect_input_counts(self.db, case_id)

        impact_matrix: list[dict[str, Any]] = []
        raw_claims: list[dict[str, Any]] = []

        for actor in actors_out[:25]:
            if actor["statement_count"] == 0 and actor["geo_risk_score"] is None:
                continue
            posture = actor["avg_posture"]
            if actor.get("mactor_avg") is not None:
                posture = (posture + actor["mactor_avg"]) / 2 if actor["statement_count"] else actor["mactor_avg"]

            trend = actor.get("posture_trend")
            trend_adj = 0.0
            if trend == "deteriorating":
                trend_adj = -0.15
            elif trend == "improving":
                trend_adj = 0.15

            for sc in scenarios:
                valence = scenario_valence(sc)
                geo_penalty = 0.0
                if actor["geo_risk_score"] is not None and valence < 0:
                    geo_penalty = -(actor["geo_risk_score"] / 100.0) * abs(valence)

                raw = posture * valence * 0.6 + geo_penalty + trend_adj * valence
                impact_score = max(-2.0, min(2.0, round(raw, 2)))

                conf_base = min(35, actor["statement_count"] * 8)
                if actor["geo_risk_score"] is not None:
                    conf_base += 15
                if actor.get("mactor_avg") is not None:
                    conf_base += 10
                if trend in ("deteriorating", "improving"):
                    conf_base += 8
                cited = filter_cited_evidence(actor["top_evidence"])
                if cited:
                    conf_base += min(25, len(cited) * 8)
                    gvals = [float(e["grounding_score"]) for e in cited if e.get("grounding_score") is not None]
                    if gvals:
                        conf_base += int(sum(gvals) / len(gvals) * 15)
                confidence = min(95, conf_base)

                scenario_prob = prob_by_name.get(sc.name, 35)
                if abs(valence) >= 0.5 and scenario_prob >= 45:
                    confidence = min(95, confidence + 5)

                mechanism_parts = []
                if valence < 0:
                    mechanism_parts.append(f"Escenari advers ({sc.name}, ~{scenario_prob}%)")
                elif valence > 0:
                    mechanism_parts.append(f"Escenari favorable ({sc.name}, ~{scenario_prob}%)")
                if actor["geo_risk_score"] is not None:
                    mechanism_parts.append(f"risc geo {actor['geo_risk_score']}/100")
                if posture != 0:
                    mechanism_parts.append(f"postura mitjana {posture:+.1f}")
                if trend:
                    mechanism_parts.append(f"tendència {trend}")
                if actor["topics"]:
                    mechanism_parts.append(f"temes: {', '.join(actor['topics'][:3])}")

                cited_ev = cited or actor["top_evidence"][:3]
                impact_matrix.append(
                    {
                        "actor": actor["name"],
                        "scenario_id": sc.id,
                        "scenario_name": sc.name,
                        "scenario_type": sc.scenario_type,
                        "scenario_probability_pct": scenario_prob,
                        "impact_score": impact_score,
                        "impact_label": impact_label(impact_score),
                        "mechanism": "; ".join(mechanism_parts),
                        "confidence": confidence,
                        "evidence": cited_ev[:3],
                    }
                )

                if abs(impact_score) >= 0.8 and confidence >= 35 and cited_ev:
                    direction = "negativament" if impact_score < 0 else "positivament"
                    raw_claims.append(
                        {
                            "claim": (
                                f"L'actor {actor['name']} es veurà afectat {direction} "
                                f"sota «{sc.name}» (impacte {impact_score:+.1f}/2, "
                                f"probabilitat escenari ~{scenario_prob}%)."
                            ),
                            "confidence": confidence,
                            "scenario_name": sc.name,
                            "scenario_probability_pct": scenario_prob,
                            "actors": [actor["name"]],
                            "impact_score": impact_score,
                            "evidence": cited_ev[:3],
                            "method": (
                                "postures OSINT + MACTOR + risc geo + tendència retrospectiva + "
                                "valència d'escenari"
                            ),
                        }
                    )

        raw_claims.sort(key=lambda c: (-abs(c.get("impact_score", 0)), -c.get("confidence", 0)))
        validation = validate_claims(raw_claims)
        claims = validation["supported_claims"][:25] or raw_claims[:15]

        overall_conf = (
            round(sum(c["confidence"] for c in claims[:10]) / max(len(claims[:10]), 1), 1)
            if claims
            else 0.0
        )

        return {
            "case_id": case_id,
            "project_id": pid,
            "actors": actors_out,
            "scenarios": scenarios_out,
            "scenario_justifications": scenario_justifications,
            "osint_signals": osint_signals,
            "impact_matrix": impact_matrix,
            "claims": claims,
            "validation": validation,
            "summary": {
                "actor_count": len(actors_out),
                "scenario_count": len(scenarios_out),
                "claim_count": len(claims),
                "overall_confidence": overall_conf,
                "export_ready": validation.get("export_ready", False),
                "top_exposed": [
                    row["actor"]
                    for row in sorted(impact_matrix, key=lambda x: x["impact_score"])[:5]
                ],
                "most_likely_scenario": max(
                    scenario_justifications,
                    key=lambda j: j["estimated_probability_pct"],
                    default={},
                ).get("scenario_name"),
            },
            "has_data": bool(actors_out and (impact_matrix or claims)),
            "input_snapshot": input_snapshot,
        }

    async def save_assessment(self, case_id: int, data: dict[str, Any]) -> ActorImpactAssessment:
        row = ActorImpactAssessment(
            case_id=case_id,
            project_id=data.get("project_id"),
            assessment_data=data,
            confidence_score=float((data.get("summary") or {}).get("overall_confidence") or 0),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_latest(self, case_id: int) -> dict[str, Any] | None:
        r = await self.db.execute(
            select(ActorImpactAssessment)
            .where(ActorImpactAssessment.case_id == case_id)
            .order_by(ActorImpactAssessment.created_at.desc())
            .limit(1)
        )
        row = r.scalar_one_or_none()
        if not row:
            return None
        data = dict(row.assessment_data or {})
        data["assessment_id"] = row.id
        data["saved_at"] = row.created_at.isoformat() if row.created_at else None
        from services.case_recalc_service import is_actor_impact_stale

        data["data_freshness"] = await is_actor_impact_stale(self.db, case_id, data)
        return data

    async def analyze_and_save(self, case_id: int, project_id: int | None = None) -> dict[str, Any]:
        data = await self.build_assessment(case_id, project_id=project_id)
        if data.get("has_data"):
            await self.save_assessment(case_id, data)
        return data
