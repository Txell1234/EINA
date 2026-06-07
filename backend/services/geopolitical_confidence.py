"""Geopolitical Confidence Index (ICG) — rule-based, traceable components for financial crossover."""
from __future__ import annotations

import math
from typing import Any

from services.actor_impact_utils import canonical_actor

GPR_SIGMOID_M = 68.0
GPR_SIGMOID_K = 0.085
GPR_MULTIPLIER_MIN = 0.85
GPR_MULTIPLIER_MAX = 1.80

_COMPONENT_BASE_WEIGHTS: dict[str, float] = {
    "osint_traceability": 0.25,
    "geopolitical_risk_environment": 0.25,
    "scenario_outlook": 0.20,
    "focus_entity_exposure": 0.15,
    "eina_gma": 0.10,
}

_GEO_RISK_TERMS = frozenset(
    {
        "sanction", "embargo", "ofac", "blockade", "conflict", "war", "tension",
        "geopolitical", "hostility", "tariff", "export control", "nuclear",
        "missile", "naval", "strait", "hormuz", "taiwan", "ukraine", "iran",
        "sanció", "embarg", "conflicte", "guerra", "tensió", "hostilitat",
    }
)

_SANCTION_KEYWORDS: dict[str, float] = {
    "embargo": 25.0,
    "ofac": 30.0,
    "sanction": 28.0,
    "sanció": 28.0,
    "blockade": 35.0,
    "bloqueig": 35.0,
    "export control": 22.0,
    "export ban": 26.0,
    "asset freeze": 32.0,
    "blacklist": 24.0,
    "secondary sanction": 30.0,
}

_SANCTION_SECTORS = frozenset({"shipping", "energy", "defense", "defence", "oil", "gas", "naval"})

_ENTITY_ICE_BASE_WEIGHTS: dict[str, float] = {
    "case_baseline": 0.35,
    "entity_policy_exposure": 0.20,
    "entity_osint_exposure": 0.15,
    "entity_sanction_exposure": 0.15,
    "entity_financial_signal": 0.10,
    "entity_scenario_fit": 0.15,
}

_SHIPPING_SECTORS = frozenset({"shipping", "naval", "maritime", "logistics"})
_DEFENSE_SECTORS = frozenset({"defense", "defence", "aerospace"})
_ENERGY_SECTORS = frozenset({"energy", "oil", "gas", "petroleum"})


def gpr_multiplier_sigmoid(avg_geopolitical_risk: float | None) -> float:
    if avg_geopolitical_risk is None or avg_geopolitical_risk < 0:
        return 1.0
    exponent = -GPR_SIGMOID_K * (float(avg_geopolitical_risk) - GPR_SIGMOID_M)
    mult = GPR_MULTIPLIER_MIN + (GPR_MULTIPLIER_MAX - GPR_MULTIPLIER_MIN) / (1 + math.exp(exponent))
    return round(mult, 4)


def _stability_factor(scenario_type: str | None, scenario_name: str | None) -> float:
    st = (scenario_type or "").lower()
    name = (scenario_name or "").lower()
    if st in ("inferno", "infern", "conflict", "conflicte") or "infern" in name or "conflicte" in name:
        return 0.2
    if st in ("tension", "tensio", "tensió") or "tens" in name:
        return 0.6
    if st in ("equilibrium", "equilibri", "cel", "eden") or "equilibri" in name or "cel" in name:
        return 1.0
    return 0.8


def _compute_osint_traceability(impact: dict[str, Any]) -> dict[str, Any] | None:
    summary = impact.get("summary") or {}
    validation = impact.get("validation") or {}
    oc = summary.get("overall_confidence")
    if oc is None or float(oc) <= 0:
        return None
    claim_count = int(summary.get("claim_count") or 0)
    export_ready = bool(validation.get("export_ready") or summary.get("export_ready"))
    export_factor = 1.0 if export_ready else 0.85
    value = min(95.0, float(oc) * (0.6 + 0.04 * min(claim_count, 10)) * export_factor)
    return {
        "name": "osint_traceability",
        "label": "Traçabilitat OSINT",
        "value": round(value, 1),
        "base_weight": _COMPONENT_BASE_WEIGHTS["osint_traceability"],
        "because": (
            f"{claim_count} claims · confiança global {float(oc):.0f}%"
            f"{' · export-ready' if export_ready else ''}"
        ),
    }


def _compute_geopolitical_risk_environment(osint_signals: dict[str, Any]) -> dict[str, Any] | None:
    if not osint_signals:
        return None
    avg_geo = osint_signals.get("avg_geopolitical_risk")
    if avg_geo is None:
        return None
    hostility = float(osint_signals.get("hostility_ratio") or 0)
    conflicts = int(osint_signals.get("conflict_events") or 0)
    value = max(0.0, min(100.0, 100.0 - float(avg_geo) - 8.0 * hostility - min(15.0, conflicts * 3)))
    return {
        "name": "geopolitical_risk_environment",
        "label": "Entorn de risc geo",
        "value": round(value, 1),
        "base_weight": _COMPONENT_BASE_WEIGHTS["geopolitical_risk_environment"],
        "because": (
            f"100 − risc mitjà {float(avg_geo):.1f}/100"
            f" − hostilitat {hostility:.0%}"
            + (f" − {conflicts} esdeveniments conflicte" if conflicts else "")
        ),
    }


def _compute_scenario_outlook(impact: dict[str, Any]) -> dict[str, Any] | None:
    justs = impact.get("scenario_justifications") or []
    if not justs:
        return None
    weighted_sum = 0.0
    prob_sum = 0.0
    parts: list[str] = []
    for j in justs[:8]:
        prob = j.get("estimated_probability_pct")
        if prob is None:
            continue
        p = float(prob)
        stability = _stability_factor(j.get("scenario_type"), j.get("scenario_name"))
        weighted_sum += p * stability
        prob_sum += p
        if j.get("scenario_name"):
            parts.append(f"«{j['scenario_name']}» {p:.0f}%×{stability:.1f}")
    if prob_sum <= 0:
        return None
    value = round(100.0 * weighted_sum / prob_sum, 1)
    return {
        "name": "scenario_outlook",
        "label": "Estabilitat escenaris Godet",
        "value": value,
        "base_weight": _COMPONENT_BASE_WEIGHTS["scenario_outlook"],
        "because": "Probabilitat ponderada per valència: " + "; ".join(parts[:4]),
    }


def _compute_focus_entity_exposure(
    impact: dict[str, Any],
    *,
    focus_company: str | None,
    entity_focus_match: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not focus_company:
        return None
    key = canonical_actor(focus_company).lower()
    claim_confs = [
        float(c["confidence"])
        for c in (impact.get("claims") or [])
        if c.get("confidence") is not None
        and (
            key in (c.get("claim") or "").lower()
            or any(key in canonical_actor(a).lower() for a in (c.get("actors") or []))
        )
    ]
    policy_score = 72.0 if entity_focus_match else 45.0
    claim_score = sum(claim_confs) / len(claim_confs) if claim_confs else None
    geo_scores: list[float] = []
    for actor in impact.get("actors") or []:
        aname = canonical_actor(actor.get("name") or "").lower()
        if key in aname or aname in key:
            grs = actor.get("geo_risk_score")
            if grs is not None:
                geo_scores.append(max(0.0, 100.0 - float(grs)))
    scores = [policy_score]
    if claim_score is not None:
        scores.append(claim_score)
    if geo_scores:
        scores.append(sum(geo_scores) / len(geo_scores))
    if len(scores) <= 1 and claim_score is None:
        return None
    value = round(sum(scores) / len(scores), 1)
    return {
        "name": "focus_entity_exposure",
        "label": f"Exposició {focus_company}",
        "value": value,
        "base_weight": _COMPONENT_BASE_WEIGHTS["focus_entity_exposure"],
        "because": (
            f"Policy×Indústria {'match' if entity_focus_match else 'sense match'}"
            + (f" · {len(claim_confs)} claims focus" if claim_confs else "")
            + (f" · risc geo actor {geo_scores[0]:.0f}/100" if geo_scores else "")
        ),
    }


def _claim_text(claim: dict[str, Any]) -> str:
    return (claim.get("claim") or claim.get("text") or "").lower()


def compute_eina_gma(
    impact: dict[str, Any],
    *,
    policy_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    EINA-GMA (Geo Market Attention) — case-specific attention score.
    GMA = 100 × (0.45×freq + 0.35×sentiment + 0.20×institutional)
    """
    claims = impact.get("claims") or []
    summary = impact.get("summary") or {}
    overall = float(summary.get("overall_confidence") or 50.0)
    geo_claims = 0
    for c in claims:
        text = _claim_text(c)
        if any(term in text for term in _GEO_RISK_TERMS):
            geo_claims += 1
    freq = geo_claims / max(1, len(claims))
    sentiment = max(0.0, min(1.0, (100.0 - overall) / 100.0))
    inst_scores: list[float] = []
    for actor in impact.get("actors") or []:
        posture = actor.get("posture_strength") or actor.get("mactor_score")
        if posture is not None:
            inst_scores.append(min(100.0, max(0.0, float(posture))))
    for row in policy_rows or []:
        if row.get("registry_found") or row.get("beneficiary_rationale"):
            inst_scores.append(72.0)
        sectors = {str(s).lower() for s in (row.get("sectors") or [])}
        if sectors & _SANCTION_SECTORS:
            inst_scores.append(68.0)
    institutional = sum(inst_scores) / len(inst_scores) if inst_scores else 45.0
    if not claims and not inst_scores:
        return None
    value = round(100.0 * (0.45 * freq + 0.35 * sentiment + 0.20 * (institutional / 100.0)), 1)
    return {
        "name": "eina_gma",
        "label": "EINA-GMA (atenció geo)",
        "value": value,
        "base_weight": _COMPONENT_BASE_WEIGHTS["eina_gma"],
        "because": (
            f"{geo_claims}/{len(claims) or 0} claims geo-risc · "
            f"incertesa OSINT {100.0 - overall:.0f}% · institucional {institutional:.0f}/100"
        ),
        "formula_detail": (
            "GMA = 100×(0.45×freq_geo_claims + 0.35×(100−overall_conf)/100 + 0.20×institutional/100)"
        ),
        "components_detail": {
            "freq_geo_claims": round(freq * 100, 1),
            "sentiment_uncertainty": round(sentiment * 100, 1),
            "institutional_score": round(institutional, 1),
        },
    }


def _scenario_adjustments_for_sis(score: float) -> dict[str, int]:
    if score < 55:
        return {}
    delta = min(25, int((score - 55) / 2) + 5)
    return {
        "Equilibri": -delta,
        "equilibri": -delta,
        "Cel": -delta,
        "Conflicte": delta,
        "conflicte": delta,
        "Inferno": delta,
        "infern": delta,
        "Tensió": max(5, delta // 2),
        "tension": max(5, delta // 2),
    }


def compute_sanction_impact(
    impact: dict[str, Any],
    *,
    scenarios: list[dict[str, Any]] | None = None,
    focus_company: str | None = None,
    policy_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Sanction Impact Score (SIS) — informational; does not enter ICG blend.
    Rule-based keyword matching on verifiable claims + impact_matrix actors.
    """
    claims = impact.get("claims") or []
    osint = impact.get("osint_signals") or {}
    drivers: list[dict[str, Any]] = []
    entity_scores: dict[str, dict[str, Any]] = {}

    for i, c in enumerate(claims):
        text = _claim_text(c)
        for kw, weight in _SANCTION_KEYWORDS.items():
            if kw in text:
                drivers.append(
                    {
                        "type": kw.replace(" ", "_"),
                        "source": f"claim_{i}",
                        "excerpt": (c.get("claim") or c.get("text") or "")[:160],
                        "weight": weight,
                    }
                )
                for actor in c.get("actors") or []:
                    key = canonical_actor(str(actor))
                    if key:
                        entry = entity_scores.setdefault(
                            key,
                            {"entity": key, "entity_type": "actor", "score": 0.0, "hits": 0},
                        )
                        entry["score"] += weight
                        entry["hits"] += 1
                break

    for row in impact.get("impact_matrix") or []:
        score = abs(float(row.get("impact_score") or 0))
        if score < 0.5:
            continue
        actor = row.get("actor") or ""
        key = canonical_actor(actor)
        if not key:
            continue
        entry = entity_scores.setdefault(
            key,
            {"entity": key, "entity_type": "actor", "score": 0.0, "hits": 0},
        )
        entry["score"] += score * 15.0
        entry["hits"] += 1

    countries = osint.get("countries_at_risk") or []
    if isinstance(countries, int):
        countries = list(range(countries))
    for country in countries[:8]:
        cname = str(country) if not isinstance(country, dict) else country.get("country") or country.get("name")
        if not cname:
            continue
        entity_scores[str(cname)] = {
            "entity": str(cname),
            "entity_type": "country",
            "score": float(osint.get("avg_geopolitical_risk") or 60.0),
            "hits": 1,
        }

    focus_key = canonical_actor(focus_company or "").lower() if focus_company else ""
    for row in policy_rows or []:
        name = row.get("name") or ""
        sectors = {str(s).lower() for s in (row.get("sectors") or [])}
        bonus = 12.0 if sectors & _SANCTION_SECTORS else 0.0
        if bonus or (focus_key and focus_key in canonical_actor(name).lower()):
            key = canonical_actor(name)
            entry = entity_scores.setdefault(
                key,
                {"entity": key, "entity_type": "company", "score": 0.0, "hits": 0},
            )
            entry["score"] += 40.0 + bonus
            entry["hits"] += 1

    raw = sum(d["weight"] for d in drivers)
    matrix_boost = min(30.0, sum(e["score"] for e in entity_scores.values()) / max(1, len(entity_scores)))
    sis = round(min(100.0, raw * 0.35 + matrix_boost + float(osint.get("hostility_ratio") or 0) * 20), 1)
    adjustments = _scenario_adjustments_for_sis(sis)

    entity_impacts: list[dict[str, Any]] = []
    for entry in sorted(entity_scores.values(), key=lambda x: x["score"], reverse=True)[:6]:
        norm = min(100.0, entry["score"] / max(1, entry["hits"]))
        prob_adj = -int(norm * 0.2) if entry["entity_type"] == "country" else -int(norm * 0.12)
        entity_impacts.append(
            {
                "entity": entry["entity"],
                "entity_type": entry["entity_type"],
                "score": round(norm, 1),
                "prob_adjust_pp": prob_adj if sis >= 60 else 0,
                "because": f"{entry['hits']} senyal(s) sanció/conflicte · score agregat {norm:.0f}",
            }
        )

    trend_signals: list[str] = []
    hostility = float(osint.get("hostility_ratio") or 0)
    conflicts = int(osint.get("conflict_events") or 0)
    if hostility >= 0.3:
        trend_signals.append(f"hostility_ratio {hostility:.0%}")
    if conflicts:
        trend_signals.append(f"conflict_events +{conflicts}")

    return {
        "sanction_impact_score": sis if drivers or entity_impacts else None,
        "drivers": drivers[:12],
        "scenario_probability_adjustments": adjustments,
        "entity_impacts": entity_impacts,
        "trend_signals": trend_signals,
    }


def apply_gpr_dynamic_weights(
    components: list[dict[str, Any]],
    avg_geopolitical_risk: float | None,
) -> list[dict[str, Any]]:
    multiplier = gpr_multiplier_sigmoid(avg_geopolitical_risk)
    out: list[dict[str, Any]] = []
    for c in components:
        entry = dict(c)
        bw = float(entry.get("base_weight") or 0)
        if entry.get("name") == "geopolitical_risk_environment":
            entry["weight"] = round(bw * multiplier, 4)
            entry["gpr_multiplier"] = multiplier
        else:
            entry["weight"] = round(bw, 4)
        out.append(entry)
    total = sum(float(c["weight"]) for c in out)
    if total > 0:
        for c in out:
            c["weight"] = round(float(c["weight"]) / total, 4)
    return out


def _weighted_index(components: list[dict[str, Any]]) -> float | None:
    if not components:
        return None
    total_w = sum(float(c["weight"]) for c in components)
    if total_w <= 0:
        return None
    return round(
        sum(float(c["value"]) * float(c["weight"]) for c in components) / total_w,
        1,
    )


def _normalize_entity_weights(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in components:
        entry = dict(c)
        entry["weight"] = round(float(entry.get("base_weight") or 0), 4)
        out.append(entry)
    total = sum(float(c["weight"]) for c in out)
    if total > 0:
        for c in out:
            c["weight"] = round(float(c["weight"]) / total, 4)
    return out


def _icg_detail(
    components: list[dict[str, Any]],
    *,
    label: str,
    avg_gpr: float | None,
) -> tuple[str, str]:
    if not components:
        return "missing", "Sense dades OSINT/escenaris — executa intel·ligència al cas."
    idx = _weighted_index(components)
    source = "computed" if len(components) >= 3 else "partial"
    detail_parts = [f"{c['label']} {c['value']}% (pes {c['weight'] * 100:.0f}%)" for c in components]
    detail = f"{label} {idx}%: " + "; ".join(detail_parts)
    if avg_gpr is not None:
        detail += f". GPR cas {float(avg_gpr):.1f} → mult {gpr_multiplier_sigmoid(avg_gpr):.2f}"
    return source, detail


def _collect_case_raw_components(
    impact: dict[str, Any],
    *,
    policy_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    osint_signals = impact.get("osint_signals") or {}
    raw: list[dict[str, Any]] = []
    for comp in (
        _compute_osint_traceability(impact),
        _compute_geopolitical_risk_environment(osint_signals),
        _compute_scenario_outlook(impact),
        compute_eina_gma(impact, policy_rows=policy_rows),
    ):
        if comp is not None:
            raw.append(comp)
    gma_detail = next((c for c in raw if c.get("name") == "eina_gma"), {})
    return raw, gma_detail


def build_case_icg_bundle(
    impact: dict[str, Any],
    *,
    policy_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """ICG_cas — shared case frame without entity focus."""
    osint_signals = impact.get("osint_signals") or {}
    avg_gpr = osint_signals.get("avg_geopolitical_risk")
    raw_components, gma_detail = _collect_case_raw_components(impact, policy_rows=policy_rows)
    components = apply_gpr_dynamic_weights(raw_components, avg_gpr)
    icg = _weighted_index(components)
    source, detail = _icg_detail(components, label="ICG_cas", avg_gpr=avg_gpr)
    if icg is None:
        source = "missing"
        detail = "Sense dades OSINT/escenaris — executa intel·ligència al cas."
    return {
        "index": icg,
        "confidence_source": source,
        "confidence_detail": detail,
        "components": components,
        "formula": "ICG_cas = Σ(value×weight)/Σ(weight); pes risc geo ajustat per sigmoid(GPR cas)",
        "gpr_case_level": round(float(avg_gpr), 1) if avg_gpr is not None else None,
        "gpr_multiplier_applied": gpr_multiplier_sigmoid(avg_gpr),
        "eina_gma": gma_detail.get("value"),
        "eina_gma_formula": gma_detail.get("formula_detail"),
        "eina_gma_components": gma_detail.get("components_detail"),
    }


def _entity_key(name: str) -> str:
    return canonical_actor(name).lower()


def _compute_entity_policy_exposure(
    *,
    focus_company: str,
    registry_row: dict[str, Any] | None,
    entity_focus_match: dict[str, Any] | None,
) -> dict[str, Any]:
    score = 50.0
    sectors = {str(s).lower() for s in (registry_row or {}).get("sectors") or []}
    roles = {str(r).lower() for r in (registry_row or {}).get("roles") or []}
    region = (registry_row or {}).get("region") or ""
    if entity_focus_match:
        score += 22.0
    if registry_row and registry_row.get("beneficiary_rationale"):
        score += 8.0
    if registry_row and registry_row.get("confidence") == "high":
        score += 5.0
    if sectors & _SHIPPING_SECTORS:
        score -= 20.0
    elif sectors & _ENERGY_SECTORS:
        score -= 14.0
    elif sectors & _DEFENSE_SECTORS:
        score -= 8.0
    if "market_opportunity" in roles:
        score += 10.0
    if region == "overseas":
        score -= 4.0
    value = round(max(5.0, min(95.0, score)), 1)
    sector_txt = ", ".join(sorted(sectors)[:3]) if sectors else "sense sector"
    return {
        "name": "entity_policy_exposure",
        "label": f"Policy×Indústria ({focus_company})",
        "value": value,
        "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_policy_exposure"],
        "because": (
            f"Sector {sector_txt} · "
            f"Policy {'match' if entity_focus_match else 'sense match'}"
            + (f" · regió {region}" if region else "")
        ),
    }


def _compute_entity_osint_exposure(
    impact: dict[str, Any],
    *,
    focus_company: str,
) -> dict[str, Any] | None:
    key = _entity_key(focus_company)
    claim_confs = [
        float(c["confidence"])
        for c in (impact.get("claims") or [])
        if c.get("confidence") is not None
        and (
            key in (c.get("claim") or "").lower()
            or any(key in _entity_key(str(a)) for a in (c.get("actors") or []))
        )
    ]
    geo_scores: list[float] = []
    for actor in impact.get("actors") or []:
        aname = _entity_key(actor.get("name") or "")
        if key in aname or aname in key:
            grs = actor.get("geo_risk_score")
            if grs is not None:
                geo_scores.append(max(0.0, 100.0 - float(grs)))
    if not claim_confs and not geo_scores:
        return None
    scores: list[float] = []
    if claim_confs:
        scores.append(sum(claim_confs) / len(claim_confs))
    if geo_scores:
        scores.append(sum(geo_scores) / len(geo_scores))
    value = round(sum(scores) / len(scores), 1)
    return {
        "name": "entity_osint_exposure",
        "label": f"OSINT entitat ({focus_company})",
        "value": value,
        "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_osint_exposure"],
        "because": (
            (f"{len(claim_confs)} claims vinculats" if claim_confs else "")
            + (f" · risc geo actor {geo_scores[0]:.0f}/100" if geo_scores else "")
        ).strip(" ·"),
    }


def _compute_entity_sanction_exposure(
    *,
    focus_company: str,
    entity_impacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    key = _entity_key(focus_company)
    matched: dict[str, Any] | None = None
    for entry in entity_impacts:
        ent_key = _entity_key(str(entry.get("entity") or ""))
        if key in ent_key or ent_key in key:
            matched = entry
            break
    if not matched:
        return {
            "name": "entity_sanction_exposure",
            "label": f"Sancions ({focus_company})",
            "value": 72.0,
            "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_sanction_exposure"],
            "because": "Sense senyal sanció directe per aquesta entitat al cas.",
        }
    sanction_score = float(matched.get("score") or 0)
    value = round(max(5.0, min(95.0, 100.0 - sanction_score)), 1)
    return {
        "name": "entity_sanction_exposure",
        "label": f"Sancions ({focus_company})",
        "value": value,
        "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_sanction_exposure"],
        "because": matched.get("because") or f"Score sanció entitat {sanction_score:.0f}/100",
    }


def _compute_entity_financial_signal(
    external_metrics: dict[str, Any] | None,
    *,
    focus_company: str,
) -> dict[str, Any] | None:
    if not external_metrics:
        return None
    iw = external_metrics.get("investwatch_summary") or {}
    ret = iw.get("avg_return_score")
    risk = iw.get("avg_risk_score")
    scores: list[float] = []
    if ret is not None:
        scores.append((float(ret) / 7.0) * 100.0)
    if risk is not None:
        scores.append((1.0 - float(risk) / 7.0) * 100.0)
    rec = (external_metrics.get("recommendation") or "").upper()
    if rec == "BUY":
        scores.append(78.0)
    elif rec == "SELL":
        scores.append(32.0)
    elif rec == "HOLD":
        scores.append(55.0)
    if not scores:
        return None
    value = round(max(5.0, min(95.0, sum(scores) / len(scores))), 1)
    parts: list[str] = []
    if ret is not None:
        parts.append(f"retorn {ret}/7")
    if risk is not None:
        parts.append(f"risc {risk}/7")
    if rec:
        parts.append(rec)
    return {
        "name": "entity_financial_signal",
        "label": f"Informe financer ({focus_company})",
        "value": value,
        "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_financial_signal"],
        "because": "InvestWatch/PRAAMS: " + ", ".join(parts),
    }


def _compute_entity_scenario_fit(
    impact: dict[str, Any],
    *,
    focus_company: str,
    registry_row: dict[str, Any] | None,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    justs = impact.get("scenario_justifications") or []
    if not justs and not scenarios:
        return None
    sectors = {str(s).lower() for s in (registry_row or {}).get("sectors") or []}
    weighted_sum = 0.0
    prob_sum = 0.0
    parts: list[str] = []
    for j in justs[:8]:
        prob = j.get("estimated_probability_pct")
        if prob is None:
            continue
        p = float(prob)
        stability = _stability_factor(j.get("scenario_type"), j.get("scenario_name"))
        st = (j.get("scenario_type") or "").lower()
        name = (j.get("scenario_name") or "").lower()
        if sectors & _SHIPPING_SECTORS and stability < 0.7:
            stability *= 0.55
        elif sectors & _DEFENSE_SECTORS and ("tens" in st or "tens" in name):
            stability = min(1.0, stability * 1.15)
        elif sectors & _ENERGY_SECTORS and ("conflict" in st or "conflicte" in name):
            stability *= 0.65
        weighted_sum += p * stability
        prob_sum += p
        if j.get("scenario_name"):
            parts.append(f"«{j['scenario_name']}» {p:.0f}%×{stability:.2f}")
    if prob_sum <= 0:
        for sc in (scenarios or [])[:6]:
            prob = sc.get("probability")
            if prob is None:
                continue
            p = float(prob) if not isinstance(prob, str) else float(prob.replace("%", ""))
            stability = _stability_factor(sc.get("type"), sc.get("name"))
            if sectors & _SHIPPING_SECTORS and stability < 0.7:
                stability *= 0.55
            weighted_sum += p * stability
            prob_sum += p
    if prob_sum <= 0:
        return None
    value = round(100.0 * weighted_sum / prob_sum, 1)
    return {
        "name": "entity_scenario_fit",
        "label": f"Ajust escenaris ({focus_company})",
        "value": value,
        "base_weight": _ENTITY_ICE_BASE_WEIGHTS["entity_scenario_fit"],
        "because": "Encaix sector × escenaris: " + ("; ".join(parts[:3]) if parts else "Godet prospectiu"),
    }


def build_entity_icg_bundle(
    impact: dict[str, Any],
    *,
    focus_company: str,
    case_icg: dict[str, Any],
    entity_focus_match: dict[str, Any] | None = None,
    registry_row: dict[str, Any] | None = None,
    external_metrics: dict[str, Any] | None = None,
    sanction_entity_impacts: list[dict[str, Any]] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """ICE_entitat — entity-specific confidence anchored to ICG_cas."""
    case_index = case_icg.get("index")
    if case_index is None:
        return None
    raw: list[dict[str, Any]] = [
        {
            "name": "case_baseline",
            "label": "Baseline ICG cas",
            "value": float(case_index),
            "base_weight": _ENTITY_ICE_BASE_WEIGHTS["case_baseline"],
            "because": f"Marc geopolític compartit del cas ({case_index}%).",
        },
        _compute_entity_policy_exposure(
            focus_company=focus_company,
            registry_row=registry_row,
            entity_focus_match=entity_focus_match,
        ),
    ]
    osint_comp = _compute_entity_osint_exposure(impact, focus_company=focus_company)
    if osint_comp:
        raw.append(osint_comp)
    sanction_comp = _compute_entity_sanction_exposure(
        focus_company=focus_company,
        entity_impacts=sanction_entity_impacts or [],
    )
    if sanction_comp:
        raw.append(sanction_comp)
    fin_comp = _compute_entity_financial_signal(external_metrics, focus_company=focus_company)
    if fin_comp:
        raw.append(fin_comp)
    scen_comp = _compute_entity_scenario_fit(
        impact,
        focus_company=focus_company,
        registry_row=registry_row,
        scenarios=scenarios,
    )
    if scen_comp:
        raw.append(scen_comp)
    components = _normalize_entity_weights(raw)
    ice = _weighted_index(components)
    if ice is None:
        return None
    delta = round(ice - float(case_index), 1)
    source, detail = _icg_detail(components, label="ICE", avg_gpr=case_icg.get("gpr_case_level"))
    return {
        "index": ice,
        "focus_company": focus_company,
        "confidence_source": source,
        "confidence_detail": detail,
        "components": components,
        "formula": "ICE = Σ(value×weight)/Σ(weight); baseline cas + exposició entitat",
        "delta_vs_case": delta,
    }


def _resolve_investment_posture(inv_recs: list[dict[str, Any]]) -> dict[str, Any]:
    if not inv_recs:
        return {"recommendation": None, "confidence_pct": None, "source": "missing", "rationale": ""}
    rec = inv_recs[0]
    rec_type = (rec.get("type") or "HOLD").upper()
    conf = rec.get("confidence_pct")
    conf_f = float(conf) if conf is not None else None
    if conf_f == 50.0 and rec_type == "HOLD":
        source = "default_fallback"
    elif conf_f is not None:
        source = "investment_recommendation"
    else:
        source = "missing"
    return {
        "recommendation": rec_type,
        "confidence_pct": conf_f,
        "source": source,
        "rationale": (rec.get("rationale") or "")[:300],
    }


def build_geopolitical_confidence_bundle(
    impact: dict[str, Any],
    *,
    inv_recs: list[dict[str, Any]] | None = None,
    focus_company: str | None = None,
    entity_focus_match: dict[str, Any] | None = None,
    policy_rows: list[dict[str, Any]] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
    registry_row: dict[str, Any] | None = None,
    external_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inv_recs = inv_recs or []
    osint_signals = impact.get("osint_signals") or {}
    avg_gpr = osint_signals.get("avg_geopolitical_risk")

    case_icg = build_case_icg_bundle(impact, policy_rows=policy_rows)
    sis = compute_sanction_impact(
        impact,
        scenarios=scenarios,
        focus_company=focus_company,
        policy_rows=policy_rows,
    )
    posture = _resolve_investment_posture(inv_recs)

    entity_icg: dict[str, Any] | None = None
    entity_posture: dict[str, Any] | None = None
    if focus_company:
        entity_icg = build_entity_icg_bundle(
            impact,
            focus_company=focus_company,
            case_icg=case_icg,
            entity_focus_match=entity_focus_match,
            registry_row=registry_row,
            external_metrics=external_metrics,
            sanction_entity_impacts=sis.get("entity_impacts") or [],
            scenarios=scenarios,
        )
        from services.crossover_recommendation_service import (
            _external_signal,
            build_entity_investment_posture,
        )

        ext_sig = _external_signal(external_metrics or {}) if external_metrics else None
        entity_posture = build_entity_investment_posture(
            focus_entity=focus_company,
            case_posture=posture,
            entity_ice=entity_icg.get("index") if entity_icg else None,
            case_icg=case_icg.get("index"),
            entity_delta=entity_icg.get("delta_vs_case") if entity_icg else None,
            external_signal=ext_sig if ext_sig != "MONITOR" else None,
            private_action=None,
            scenarios=scenarios,
        )

    entity_index = entity_icg.get("index") if entity_icg else None
    entity_delta = entity_icg.get("delta_vs_case") if entity_icg else None

    icg = case_icg.get("index")
    components = case_icg.get("components") or []
    source = case_icg.get("confidence_source") or "missing"
    detail = case_icg.get("confidence_detail") or ""

    return {
        "case_icg": case_icg,
        "entity_icg": entity_icg,
        "entity_icg_delta": entity_delta,
        "entity_confidence_index": entity_index,
        "focus_company": focus_company,
        "geopolitical_confidence_index": icg,
        "case_geopolitical_confidence_index": icg,
        "confidence_pct": icg,
        "confidence_source": source,
        "confidence_detail": detail,
        "entity_confidence_detail": entity_icg.get("confidence_detail") if entity_icg else None,
        "geopolitical_confidence_formula": case_icg.get("formula"),
        "entity_confidence_formula": entity_icg.get("formula") if entity_icg else None,
        "geopolitical_confidence_components": components,
        "entity_confidence_components": (entity_icg.get("components") or []) if entity_icg else [],
        "components": components,
        "gpr_case_level": case_icg.get("gpr_case_level"),
        "gpr_multiplier_applied": case_icg.get("gpr_multiplier_applied"),
        "eina_gma": case_icg.get("eina_gma"),
        "eina_gma_formula": case_icg.get("eina_gma_formula"),
        "eina_gma_components": case_icg.get("eina_gma_components"),
        "sanction_impact_score": sis.get("sanction_impact_score"),
        "sanction_drivers": sis.get("drivers") or [],
        "sanction_entity_impacts": sis.get("entity_impacts") or [],
        "sanction_scenario_adjustments": sis.get("scenario_probability_adjustments") or {},
        "sanction_trend_signals": sis.get("trend_signals") or [],
        "investment_posture": posture,
        "entity_investment_posture": entity_posture,
        "investment_recommendation_pct": posture.get("confidence_pct"),
        "actor_impact_snapshot": {
            "summary": impact.get("summary"),
            "osint_signals": osint_signals,
            "has_data": impact.get("has_data"),
        },
    }
