"""Actor motivation from OSINT extraction, alert matches and MACTOR mobilisation."""
from __future__ import annotations

from typing import Any

from models.extract import ExtractedStatement
from models.prospective import AlertMatch, AlertMonitor, ProspectiveScenario
from services.actor_impact_utils import canonical_actor


def _actor_in_text(actor: str, text: str) -> bool:
    if not actor or not text:
        return False
    key = canonical_actor(actor).lower()
    if not key:
        return False
    return key in text.lower() or key.split()[0].lower() in text.lower()


def build_actor_motivation(
    actor_name: str,
    *,
    statements: list[ExtractedStatement],
    alert_matches: list[AlertMatch],
    monitors: dict[int, AlertMonitor],
    scenarios_by_id: dict[int, ProspectiveScenario],
    mactor_mobilisation: float | None = None,
    strategic_goals: list[str] | None = None,
) -> dict[str, Any]:
    """Synthesise motivation text and structured sources for one actor."""
    key = canonical_actor(actor_name)
    motivation_parts: list[str] = []
    sources: list[str] = []
    alert_signals: list[dict[str, Any]] = []

    actor_stmts = [s for s in statements if canonical_actor(s.actor or "") == key]
    if actor_stmts:
        topics: dict[str, int] = {}
        postures: list[float] = []
        contexts: list[str] = []
        for s in actor_stmts:
            if s.topic:
                topics[s.topic] = topics.get(s.topic, 0) + 1
            if s.posture_value is not None:
                postures.append(float(s.posture_value))
            if s.context and len(s.context.strip()) > 10:
                contexts.append(s.context.strip()[:160])
            if s.statement and len(s.statement.strip()) > 20:
                contexts.append(s.statement.strip()[:160])
        if topics:
            top = sorted(topics.items(), key=lambda x: -x[1])[:3]
            motivation_parts.append(
                "Interessos detectats en extracció OSINT: "
                + ", ".join(f"{t} ({n} mencions)" for t, n in top)
            )
        if postures:
            avg = sum(postures) / len(postures)
            tone = "hostil" if avg <= -0.5 else "cooperatiu" if avg >= 0.5 else "neutral"
            motivation_parts.append(
                f"Postura mitjana {avg:+.1f} ({tone}) en {len(postures)} declaració(ns) extreta(es)"
            )
        if contexts:
            motivation_parts.append(f"Context: {contexts[0]}")
        sources.append("extraction")

    for match in alert_matches:
        blob = " ".join(
            filter(
                None,
                [
                    match.title,
                    match.excerpt,
                    match.analysis_summary,
                    " ".join(match.matched_keywords or []),
                ],
            )
        )
        if not _actor_in_text(key, blob) and match.extracted_statement_id:
            linked = next(
                (s for s in statements if s.id == match.extracted_statement_id),
                None,
            )
            if not linked or canonical_actor(linked.actor or "") != key:
                continue
        elif not _actor_in_text(key, blob) and not match.extracted_statement_id:
            continue

        monitor = monitors.get(match.monitor_id)
        indicator = (monitor.indicator if monitor else "") or ""
        scenario_name = ""
        if match.scenario_id and match.scenario_id in scenarios_by_id:
            scenario_name = scenarios_by_id[match.scenario_id].name or ""

        kw = ", ".join((match.matched_keywords or [])[:5])
        alert_line = f"Alerta «{indicator[:80]}»" if indicator else "Alerta OSINT"
        if kw:
            alert_line += f" (paraules clau: {kw})"
        if scenario_name:
            alert_line += f" vinculada a l'escenari «{scenario_name}»"
        if match.analysis_summary and len(match.analysis_summary.strip()) > 20:
            alert_line += f". Anàlisi: {match.analysis_summary.strip()[:200]}"
        motivation_parts.append(alert_line)
        alert_signals.append(
            {
                "match_id": match.id,
                "monitor_id": match.monitor_id,
                "indicator": indicator[:120],
                "keywords": match.matched_keywords or [],
                "scenario_name": scenario_name,
                "source_type": match.source_type or "",
                "url": match.url or "",
            }
        )
        sources.append("alert")

    if strategic_goals:
        motivation_parts.append(
            "Objectius estratègics (prospectiva): " + "; ".join(str(g) for g in strategic_goals[:3])
        )
        sources.append("prospective")

    if mactor_mobilisation is not None and mactor_mobilisation > 0:
        level = "alta" if mactor_mobilisation >= 8 else "moderada" if mactor_mobilisation >= 4 else "baixa"
        motivation_parts.append(
            f"Mobilització MACTOR {level} (índex {mactor_mobilisation:.1f}) — implicació activa en objectius del sistema"
        )
        sources.append("mactor")

    text = " ".join(motivation_parts).strip()
    if not text:
        text = "Sense motivació estructurada encara — cal extracció OSINT, alertes o postures MACTOR."

    return {
        "text": text,
        "sources": sorted(set(sources)),
        "alert_signals": alert_signals[:8],
        "mobilisation": mactor_mobilisation,
        "statement_count": len(actor_stmts),
    }
