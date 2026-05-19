"""
Retrospective Service — Godet step 1.5

Analyses temporal evolution of actor postures from extracted OSINT statements.
Produces:
  - actor_trends: posture evolution per actor per topic, ordered by date
  - key_events: statements with highest posture magnitude (|posture_value| >= 2)
  - topic_dynamics: which topics have most conflictual/cooperative dynamics
  - micmac_evidence: for each variable-pair, how many statements support each
    influence score (used as confidence indicator for MIC-MAC cells)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime | None:
    """Try multiple date formats from OSINT sources."""
    if not date_str or date_str == "null":
        return None
    formats = [
        "%Y%m%dT%H%M%SZ",      # GDELT: 20241115T120000Z
        "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",            # Google News
        "%a, %d %b %Y %H:%M:%S %z",  # RSS
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:25], fmt)
        except (ValueError, TypeError):
            continue
    return None


def _quarter_label(dt: datetime) -> str:
    """Format datetime as Q1 2024 etc."""
    q = (dt.month - 1) // 3 + 1
    return f"Q{q} {dt.year}"


def _quarter_sort_key(label: str) -> tuple[int, int]:
    parts = label.split()
    if len(parts) == 2 and parts[0].startswith("Q"):
        try:
            return (int(parts[1]), int(parts[0][1:]))
        except ValueError:
            pass
    return (0, 0)


class RetrospectiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_retrospective(
        self, case_id: int, project_id: int | None = None
    ) -> dict[str, Any]:
        """
        Main entry point.
        Returns full retrospective analysis for a case.
        """
        _ = project_id
        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        )
        stmts = list(stmts_r.scalars().all())

        if not stmts:
            return {
                "has_data": False,
                "message": "Cap declaració extreta. Executa l'extracció OSINT primer.",
            }

        dated = []
        undated = []
        for s in stmts:
            dt = _parse_date(s.source_date or "")
            if dt:
                dated.append((dt, s))
            else:
                undated.append(s)

        dated.sort(key=lambda x: x[0])

        return {
            "has_data": True,
            "total_statements": len(stmts),
            "dated_statements": len(dated),
            "undated_statements": len(undated),
            "date_range": {
                "earliest": dated[0][0].strftime("%Y-%m-%d") if dated else None,
                "latest": dated[-1][0].strftime("%Y-%m-%d") if dated else None,
            },
            "actor_trends": self._build_actor_trends(dated),
            "topic_dynamics": self._build_topic_dynamics(stmts),
            "key_events": self._build_key_events(dated),
            "actor_posture_summary": self._build_actor_posture_summary(stmts),
            "micmac_evidence": self._build_micmac_evidence(stmts),
        }

    def _build_actor_trends(
        self, dated: list[tuple[datetime, ExtractedStatement]]
    ) -> list[dict]:
        """
        For each actor, build a timeline of their average posture per quarter.
        Returns actors sorted by number of statements (most active first).
        """
        actor_quarters: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for dt, s in dated:
            if not s.actor or not s.posture_toward:
                continue
            label = _quarter_label(dt)
            key = f"{s.actor}→{s.posture_toward}"
            actor_quarters[key][label].append(s.posture_value)

        trends = []
        for actor_target, quarters in actor_quarters.items():
            actor, target = actor_target.split("→", 1)
            timeline = []
            for q_label in sorted(quarters.keys(), key=_quarter_sort_key):
                vals = quarters[q_label]
                avg = round(sum(vals) / len(vals), 2)
                timeline.append({
                    "period": q_label,
                    "avg_posture": avg,
                    "n_statements": len(vals),
                    "min": min(vals),
                    "max": max(vals),
                })
            if len(timeline) >= 2:
                first = timeline[0]["avg_posture"]
                last = timeline[-1]["avg_posture"]
                delta = round(last - first, 2)
                trend_dir = (
                    "escalating" if delta < -0.5
                    else "improving" if delta > 0.5
                    else "stable"
                )
            else:
                delta = 0.0
                trend_dir = "insufficient_data"

            trends.append({
                "actor": actor,
                "toward": target,
                "timeline": timeline,
                "overall_delta": delta,
                "trend_direction": trend_dir,
                "total_statements": sum(len(v) for v in quarters.values()),
            })

        return sorted(trends, key=lambda x: -x["total_statements"])[:20]

    def _build_topic_dynamics(
        self, stmts: list[ExtractedStatement]
    ) -> list[dict]:
        """Per topic: average posture, most conflictual actors, most cooperative actors."""
        topic_data: dict[str, list[int]] = defaultdict(list)
        topic_actors: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for s in stmts:
            if not s.topic:
                continue
            topic_data[s.topic].append(s.posture_value)
            if s.actor:
                topic_actors[s.topic][s.actor].append(s.posture_value)

        dynamics = []
        for topic, vals in sorted(topic_data.items(), key=lambda x: -len(x[1])):
            avg = round(sum(vals) / len(vals), 2)
            actor_avgs = {
                actor: round(sum(v) / len(v), 2)
                for actor, v in topic_actors[topic].items()
            }
            dynamics.append({
                "topic": topic,
                "n_statements": len(vals),
                "avg_posture": avg,
                "most_hostile": min(actor_avgs, key=actor_avgs.get) if actor_avgs else None,
                "most_cooperative": max(actor_avgs, key=actor_avgs.get) if actor_avgs else None,
                "actor_postures": dict(sorted(actor_avgs.items(), key=lambda x: x[1])),
            })

        return dynamics[:15]

    def _build_key_events(
        self, dated: list[tuple[datetime, ExtractedStatement]]
    ) -> list[dict]:
        """
        Key events: statements with |posture_value| >= 2 (strong positions).
        These are the turning points in the retrospective.
        """
        events = []
        for dt, s in dated:
            if abs(s.posture_value) >= 2:
                events.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "period": _quarter_label(dt),
                    "actor": s.actor,
                    "toward": s.posture_toward,
                    "posture_value": s.posture_value,
                    "topic": s.topic,
                    "statement": s.statement[:200],
                    "framing": s.framing,
                    "source_url": s.source_url,
                })
        return sorted(events, key=lambda x: x["date"], reverse=True)[:30]

    def _build_actor_posture_summary(
        self, stmts: list[ExtractedStatement]
    ) -> list[dict]:
        """Summary of each actor's overall posture profile. Useful for MACTOR step."""
        actor_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"postures": [], "topics": set(), "importance": []}
        )
        for s in stmts:
            if not s.actor:
                continue
            actor_data[s.actor]["postures"].append(s.posture_value)
            if s.topic:
                actor_data[s.actor]["topics"].add(s.topic)
            actor_data[s.actor]["importance"].append(s.actor_importance)

        summary = []
        for actor, data in sorted(
            actor_data.items(), key=lambda x: -len(x[1]["postures"])
        ):
            postures = data["postures"]
            avg_pos = round(sum(postures) / len(postures), 2)
            avg_imp = round(sum(data["importance"]) / len(data["importance"]), 1)
            hostile = sum(1 for p in postures if p <= -1)
            coop = sum(1 for p in postures if p >= 1)
            summary.append({
                "actor": actor,
                "n_statements": len(postures),
                "avg_posture": avg_pos,
                "avg_importance": avg_imp,
                "hostile_pct": round(hostile / len(postures) * 100),
                "cooperative_pct": round(coop / len(postures) * 100),
                "main_topics": list(data["topics"])[:5],
                "profile": (
                    "conflictiu" if avg_pos < -0.5
                    else "cooperatiu" if avg_pos > 0.5
                    else "neutral"
                ),
            })
        return summary[:12]

    def _build_micmac_evidence(
        self, stmts: list[ExtractedStatement]
    ) -> dict[str, Any]:
        """
        For each (actor_pair or topic_pair), count statements that suggest
        influence. This provides empirical backing for MIC-MAC cell scores.
        """
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        for s in stmts:
            if s.topic and s.posture_toward:
                key = (s.topic, s.posture_toward)
                pair_counts[key] += 1

        if not pair_counts:
            return {"pairs": [], "max_count": 0}

        max_count = max(pair_counts.values())
        pairs = [
            {
                "from_topic": k[0],
                "to_topic": k[1],
                "n_statements": v,
                "confidence": round(v / max_count, 2),
            }
            for k, v in sorted(pair_counts.items(), key=lambda x: -x[1])
        ][:50]

        return {
            "pairs": pairs,
            "max_count": max_count,
            "interpretation": (
                "Usa 'from_topic → to_topic confidence' per validar les puntuacions "
                "de la matriu MIC-MAC. Alta confiança = moltes declaracions OSINT "
                "suporten la relació d'influència."
            ),
        }
