"""
Helpers for actor impact scoring, scenario justification and claim validation.
"""
from __future__ import annotations

from typing import Any

from models.extract import ExtractedStatement
from models.geopolitical import DiplomaticEvent, GeopoliticalRisk
from models.prospective import ProspectiveScenario

_DEFAULT_SCENARIO_TEMPLATES = [
    {"name": "Escenari Infern", "scenario_type": "infern", "default_probability": "BAIXA-MITJA", "default_possibility": "PLAUSIBLE"},
    {"name": "Escenari Tensió Crònica", "scenario_type": "tensio", "default_probability": "ALTA", "default_possibility": "PLAUSIBLE"},
    {"name": "Escenari Equilibri Dinàmic", "scenario_type": "equilibri", "default_probability": "MITJA", "default_possibility": "PLAUSIBLE"},
    {"name": "Escenari Cel", "scenario_type": "cel", "default_probability": "BAIXA", "default_possibility": "CONDICIONAL"},
]


def ensure_four_scenarios(scenarios: list[ProspectiveScenario]) -> list[ProspectiveScenario]:
    """Ensure all four Godet scenarios exist (merge DB rows with defaults)."""
    by_type: dict[str, ProspectiveScenario] = {}
    for sc in scenarios:
        st = (sc.scenario_type or "").lower().strip()
        if st and st not in by_type:
            by_type[st] = sc

    out: list[ProspectiveScenario] = []
    seen_types: set[str] = set()
    for tpl in _DEFAULT_SCENARIO_TEMPLATES:
        st = tpl["scenario_type"]
        seen_types.add(st)
        if st in by_type:
            out.append(by_type[st])
        else:
            out.append(
                ProspectiveScenario(
                    id=0,
                    project_id=0,
                    name=tpl["name"],
                    scenario_type=st,
                    probability=tpl["default_probability"],
                    possibility=tpl.get("default_possibility", "PLAUSIBLE"),
                    morphological_config="",
                    narrative="",
                )
            )
    for sc in scenarios:
        st = (sc.scenario_type or "").lower().strip()
        if st and st not in seen_types:
            out.append(sc)
    return out


def merge_scenario_with_justification(
    sc: ProspectiveScenario,
    justification: dict[str, Any] | None,
) -> dict[str, Any]:
    from schemas.actor_typology import SCENARIO_PROFILES

    j = justification or {}
    st = (sc.scenario_type or "").lower().strip()
    profile = SCENARIO_PROFILES.get(st, {})
    return {
        "id": sc.id,
        "name": sc.name,
        "scenario_type": sc.scenario_type,
        "scenario_label": profile.get("label"),
        "risk_profile": profile.get("risk_profile"),
        "reversibility": profile.get("reversibility"),
        "valence": profile.get("valence"),
        "horizon_months": profile.get("horizon_months"),
        "possibility": getattr(sc, "possibility", None) or "PLAUSIBLE",
        "possibility_rationale": getattr(sc, "possibility_rationale", None) or "",
        "probability": sc.probability,
        "probability_label": sc.probability,
        "base_probability_pct": j.get("base_probability_pct"),
        "estimated_probability_pct": j.get("estimated_probability_pct"),
        "adjustment_points": j.get("adjustment_points", 0),
        "config": sc.morphological_config or "",
        "narrative_excerpt": (sc.narrative or "")[:400],
        "justification": j or None,
        "supporting_signals": j.get("supporting_signals") or [],
        "contradicting_signals": j.get("contradicting_signals") or [],
        "rationale": j.get("rationale") or "",
    }

_PROB_LABEL_PCT = {
    "ALTA": 65,
    "MITJA-ALTA": 55,
    "MITJA": 35,
    "BAIXA-MITJA": 20,
    "BAIXA": 10,
}

_SCENARIO_VALENCE = {
    "infern": -1.0,
    "tensio": -0.5,
    "tensió": -0.5,
    "equilibri": 0.0,
    "cel": 1.0,
    "edèn": 1.0,
    "eden": 1.0,
}

_CONFLICT_EVENT_TYPES = frozenset({"conflict", "sanction", "cyberattack", "sanction"})

# Aliases per deduplicar actors (clau normalitzada → nom canònic)
_ACTOR_ALIASES: dict[str, str] = {
    "china": "Xina",
    "xina": "Xina",
    "prc": "Xina",
    "people's republic of china": "Xina",
    "usa": "Estats Units",
    "us": "Estats Units",
    "united states": "Estats Units",
    "estats units": "Estats Units",
    "eu": "Unió Europea",
    "european union": "Unió Europea",
    "unio europea": "Unió Europea",
    "russia": "Rússia",
    "rússia": "Rússia",
    "russian federation": "Rússia",
    "uk": "Regne Unit",
    "united kingdom": "Regne Unit",
}


def canonical_actor(name: str) -> str:
    key = " ".join((name or "").strip().split()).lower()
    if not key:
        return ""
    return _ACTOR_ALIASES.get(key, " ".join((name or "").strip().split()))


def scenario_valence(scenario: ProspectiveScenario) -> float:
    st = (scenario.scenario_type or "").lower()
    name = (scenario.name or "").lower()
    if st in _SCENARIO_VALENCE:
        return _SCENARIO_VALENCE[st]
    for key, val in _SCENARIO_VALENCE.items():
        if key in name:
            return val
    if "infern" in name or "hell" in name:
        return -1.0
    if "cel" in name or "edèn" in name or "eden" in name:
        return 1.0
    if "tensió" in name or "tensio" in name:
        return -0.5
    return 0.0


def impact_label(score: float) -> str:
    if score <= -1.5:
        return "molt_negatiu"
    if score <= -0.5:
        return "negatiu"
    if score < 0.5:
        return "neutral"
    if score < 1.5:
        return "positiu"
    return "molt_positiu"


def prob_label_to_pct(label: str | None) -> int:
    if not label:
        return 35
    normalized = label.upper().replace(" ", "-").replace("_", "-")
    for key, pct in _PROB_LABEL_PCT.items():
        if key in normalized or normalized in key:
            return pct
    return 35


def evidence_is_cited(ev: dict[str, Any]) -> bool:
    url = (ev.get("source_url") or "").strip()
    excerpt = (ev.get("excerpt") or "").strip()
    grounding = ev.get("grounding_score")
    if url.startswith("http"):
        return True
    if len(excerpt) >= 50 and (grounding is None or float(grounding) >= 0.35):
        return True
    return False


def filter_cited_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    out: list[dict[str, Any]] = []
    for ev in evidence:
        if not evidence_is_cited(ev):
            continue
        url = (ev.get("source_url") or "").strip()
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        out.append(ev)
    return out


def build_osint_signals(
    statements: list[ExtractedStatement],
    events: list[DiplomaticEvent],
    geo_risks: list[GeopoliticalRisk],
) -> dict[str, Any]:
    hostile = sum(1 for s in statements if (s.posture_value or 0) <= -1)
    cooperative = sum(1 for s in statements if (s.posture_value or 0) >= 1)
    neutral = len(statements) - hostile - cooperative
    conflict_events = 0
    for ev in events:
        et = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type or "")
        if et.lower() in _CONFLICT_EVENT_TYPES:
            conflict_events += 1
    avg_geo = 0.0
    if geo_risks:
        avg_geo = sum(float(g.overall_risk_score or 0) for g in geo_risks) / len(geo_risks)
    total = max(len(statements), 1)
    return {
        "total_statements": len(statements),
        "hostile_statements": hostile,
        "cooperative_statements": cooperative,
        "neutral_statements": neutral,
        "hostility_ratio": round(hostile / total, 2),
        "cooperation_ratio": round(cooperative / total, 2),
        "diplomatic_events": len(events),
        "conflict_events": conflict_events,
        "countries_at_risk": len(geo_risks),
        "avg_geopolitical_risk": round(avg_geo, 1),
    }


def justify_scenarios(
    scenarios: list[ProspectiveScenario],
    signals: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sc in scenarios:
        base = prob_label_to_pct(sc.probability)
        valence = scenario_valence(sc)
        adjustment = 0
        supporting: list[str] = []
        contradicting: list[str] = []

        if valence < -0.3:
            if signals["hostility_ratio"] >= 0.25:
                adj = min(15, int(signals["hostility_ratio"] * 30))
                adjustment += adj
                supporting.append(
                    f"{signals['hostile_statements']} declaracions hostils "
                    f"({int(signals['hostility_ratio'] * 100)}% del total)"
                )
            if signals["conflict_events"] > 0:
                adjustment += min(10, signals["conflict_events"] * 3)
                supporting.append(f"{signals['conflict_events']} esdeveniments de conflicte/sanció")
            if signals["avg_geopolitical_risk"] >= 55:
                adjustment += 8
                supporting.append(f"risc geo mitjà {signals['avg_geopolitical_risk']}/100")
            if signals["cooperation_ratio"] >= 0.3:
                adjustment -= min(8, int(signals["cooperation_ratio"] * 15))
                contradicting.append("alta proporció de declaracions cooperatives")

        elif valence > 0.3:
            if signals["cooperation_ratio"] >= 0.25:
                adjustment += min(12, int(signals["cooperation_ratio"] * 25))
                supporting.append(
                    f"{signals['cooperative_statements']} declaracions cooperatives"
                )
            if signals["hostility_ratio"] >= 0.35:
                adjustment -= min(12, int(signals["hostility_ratio"] * 20))
                contradicting.append("entorn encara molt hostil segons OSINT")

        estimated = min(92, max(8, base + adjustment))
        results.append(
            {
                "scenario_id": sc.id,
                "scenario_name": sc.name,
                "scenario_type": sc.scenario_type,
                "probability_label": sc.probability,
                "base_probability_pct": base,
                "estimated_probability_pct": estimated,
                "adjustment_points": adjustment,
                "supporting_signals": supporting,
                "contradicting_signals": contradicting,
                "rationale": (
                    f"Probabilitat estimada {estimated}% (base {base}% + {adjustment:+d} pts) "
                    f"segons {len(supporting)} senyal(s) OSINT observable(s)."
                    if supporting
                    else f"Probabilitat estimada {estimated}% (sense senyals OSINT suficients per ajustar la base)."
                ),
            }
        )
    return results


def validate_claims(claims: list[dict[str, Any]]) -> dict[str, Any]:
    without_source = 0
    without_citation = 0
    supported: list[dict[str, Any]] = []
    for c in claims:
        evidence = c.get("evidence") or []
        cited = filter_cited_evidence(evidence)
        has_url = any((e.get("source_url") or "").startswith("http") for e in evidence)
        if not cited:
            without_citation += 1
        if not has_url:
            without_source += 1
        entry = dict(c)
        entry["evidence"] = cited or evidence[:2]
        entry["has_cited_evidence"] = bool(cited)
        entry["has_source_url"] = has_url
        if cited:
            supported.append(entry)
    return {
        "claims_total": len(claims),
        "claims_supported": len(supported),
        "claims_without_citation": without_citation,
        "claims_without_source_url": without_source,
        "export_ready": without_citation == 0 or len(supported) >= max(1, len(claims) // 2),
        "supported_claims": supported,
    }
