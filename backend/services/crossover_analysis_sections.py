"""Deep industry + geopolitical analysis blocks for financial crossover reports."""
from __future__ import annotations

from typing import Any

from services.policy_industry_profiles import all_reference_names, ticker_for_company

_SECTOR_GEO: dict[str, str] = {
    "submarines": (
        "La dinàmica submarina Indo-Pacífic (AUKUS, Xina, Corea) condiciona compres públiques "
        "i exportacions de plataformes; escenaris de tensió retarden o redistribueixen contractes."
    ),
    "aircraft": (
        "Interoperabilitat amb aliats (F-35, patrulla marítima) i tensions comercials US-Xina "
        "afecten programes dual-use i offsets."
    ),
    "transport": (
        "Logística de defensa i mobilitat estratègica depenen de cadenes regionals i "
        "controls d'exportació dual-use."
    ),
    "naval": "Modernització de flotes regionals impulsa integradors navals i subministradors.",
    "missiles": "Defensa antí-míssil i deterrencia regional són prioritzats en polítiques públiques del cas.",
}


def _fmt_pct(metrics: dict[str, Any], label: str) -> str | None:
    for m in metrics.get("key_metrics") or []:
        if str(m.get("label", "")).lower() == label.lower():
            return f"{m.get('value_pct')}%"
    return None


def _financial_snapshot(metrics: dict[str, Any]) -> dict[str, Any]:
    iw = metrics.get("investwatch_summary") or {}
    rec = (metrics.get("primary_recommendation") or metrics.get("derived_signal") or "").upper()
    return {
        "signal": rec or "—",
        "avg_return": iw.get("avg_return_score"),
        "avg_risk": iw.get("avg_risk_score"),
        "iw_signal": iw.get("signal"),
        "upside_pct": metrics.get("upside_consensus_pct"),
        "roa": _fmt_pct(metrics, "ROA"),
        "roce": _fmt_pct(metrics, "ROCE"),
        "revenue_growth": _fmt_pct(metrics, "Revenue"),
        "earnings_growth": _fmt_pct(metrics, "Earnings"),
    }


def _scenario_context(eina: dict[str, Any]) -> dict[str, Any]:
    scenarios = eina.get("scenarios") or []
    tense = [
        s
        for s in scenarios
        if (s.get("type") or "").lower() in ("inferno", "tension", "infern", "tensio")
    ]
    dominant = max(
        scenarios,
        key=lambda s: float(s.get("probability") or 0)
        if str(s.get("probability", "")).replace(".", "", 1).isdigit()
        else 0,
        default=None,
    )
    inv = (eina.get("investment_recommendations") or [{}])[0]
    computed = eina.get("computed_confidence") or {}
    icg = computed.get("geopolitical_confidence_index")
    posture = computed.get("investment_posture") or {}
    return {
        "tense_names": [s.get("name") for s in tense[:3] if s.get("name")],
        "dominant_scenario": dominant.get("name") if dominant else None,
        "dominant_prob": dominant.get("probability") if dominant else None,
        "eina_rec": (posture.get("recommendation") or inv.get("type") or "HOLD").upper(),
        "eina_conf": icg if icg is not None else inv.get("confidence_pct"),
        "icg_conf": icg,
        "eina_rationale": (inv.get("rationale") or "")[:200],
        "actor_summary": (eina.get("actor_impact") or {}).get("summary") or {},
        "icg_components": computed.get("geopolitical_confidence_components") or [],
        "sis_score": computed.get("sanction_impact_score"),
        "sis_entity_impacts": computed.get("sanction_entity_impacts") or [],
        "sis_adjustments": computed.get("sanction_scenario_adjustments") or {},
        "eina_gma": computed.get("eina_gma"),
        "osint_signals": (eina.get("actor_impact") or {}).get("osint_signals") or {},
    }


def _peers_for_sectors(sectors: list[str], exclude_name: str) -> list[dict[str, Any]]:
    exclude_key = exclude_name.lower()
    out: list[dict[str, Any]] = []
    for prof in all_reference_names().values():
        name = prof.get("name") or ""
        if name.lower() == exclude_key or exclude_key in name.lower():
            continue
        prof_sectors = set(prof.get("sectors") or [])
        if not prof_sectors.intersection(sectors):
            continue
        out.append(
            {
                "name": name,
                "ticker": prof.get("ticker") or ticker_for_company(name),
                "roles": prof.get("roles") or [],
                "sectors": list(prof_sectors),
                "region": prof.get("region"),
                "beneficiary_rationale": (prof.get("beneficiary_rationale") or "")[:180],
                "policy_link": (prof.get("policy_link") or "")[:120],
            }
        )
    return out[:8]


def build_industry_implications(
    profile: dict[str, Any],
    metrics: dict[str, Any],
    eina: dict[str, Any],
    *,
    signal: str,
    final_numbers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Per-sector financial + geopolitical implication for the focus entity."""
    fin = _financial_snapshot(metrics)
    geo = _scenario_context(eina)
    name = profile.get("name") or "Entitat focus"
    policy = (profile.get("policy_link") or "").strip()
    rationale = (profile.get("beneficiary_rationale") or "").strip()
    sectors = profile.get("sectors") or []
    fn = final_numbers or {}

    out: list[dict[str, Any]] = []
    for sector in sectors[:5]:
        sector_label = sector.replace("_", " ").title()
        fin_parts: list[str] = []
        if fin["signal"] != "—":
            fin_parts.append(f"Senyal extern {fin['signal']}")
        if fin.get("upside_pct") is not None:
            fin_parts.append(f"upside consens {fin['upside_pct']}%")
        if fin.get("avg_return") is not None and fin.get("avg_risk") is not None:
            fin_parts.append(
                f"InvestWatch retorn {fin['avg_return']}/7 vs risc {fin['avg_risk']}/7"
            )
        if fin.get("roce"):
            fin_parts.append(f"ROCE {fin['roce']}")
        if fin.get("revenue_growth"):
            fin_parts.append(f"creixement ingressos {fin['revenue_growth']}")
        if fn.get("blended_return_index") is not None:
            fin_parts.append(f"índex combinat retorn EINA {fn['blended_return_index']}")

        geo_parts: list[str] = []
        if policy:
            geo_parts.append(policy)
        if rationale:
            geo_parts.append(rationale)
        geo_parts.append(_SECTOR_GEO.get(sector, f"Sector {sector_label} exposat a polítiques del cas."))
        if geo["tense_names"]:
            geo_parts.append(
                f"Escenaris de tensió del cas: {', '.join(geo['tense_names'])}."
            )
        if geo.get("dominant_scenario"):
            geo_parts.append(
                f"Escenari dominant: {geo['dominant_scenario']}"
                + (f" (~{geo['dominant_prob']}%)" if geo.get("dominant_prob") else "")
            )

        peers = _peers_for_sectors([sector], name)
        peer_names = [p["name"] for p in peers[:3]]

        if signal == "BUY":
            play = f"Sobreponderar exposició al sector {sector_label} via {name} o integradors del cluster."
        elif signal == "SELL":
            play = f"Reduir pes del sector {sector_label}; risc geopolític i senyal extern negatiu."
        else:
            play = f"Mantenir exposició sectorial {sector_label}; validar pipeline de compres abans d'augmentar."

        implication = (
            f"Per {name}, el sector {sector_label} combina "
            f"{' · '.join(fin_parts[:4]) or 'dades financeres limitades'} "
            f"amb el context geo-polític del cas ({policy or 'Policy×Indústria'})."
        )

        out.append(
            {
                "sector": sector,
                "sector_label": sector_label,
                "financial_read": " · ".join(fin_parts) or "Sense mètriques financeres extretes.",
                "geopolitical_read": " ".join(geo_parts[:4]),
                "implication": implication,
                "suggested_play": play,
                "peers": peer_names,
                "peer_details": peers[:4],
            }
        )
    return out


def build_geopolitical_financial_synthesis(
    profile: dict[str, Any],
    metrics: dict[str, Any],
    eina: dict[str, Any],
    *,
    final_numbers: dict[str, Any] | None = None,
    divergences: list[dict[str, Any]] | None = None,
    alignments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Structured bridge between InvestWatch numbers and case geopolitics."""
    fin = _financial_snapshot(metrics)
    geo = _scenario_context(eina)
    name = profile.get("name") or "L'entitat"
    fn = final_numbers or {}
    paragraphs: list[str] = []

    fin_line = [f"Informe extern sobre {name}: {fin['signal']}."]
    if fin.get("upside_pct") is not None:
        fin_line.append(f"Upside consens analistes ~{fin['upside_pct']}%.")
    if fin.get("avg_return") is not None:
        fin_line.append(
            f"PRAAMS retorn mitjà {fin['avg_return']}/7 vs risc {fin['avg_risk']}/7."
        )
    if fin.get("roa") or fin.get("roce"):
        fin_line.append(
            f"Ratios clau: ROA {fin.get('roa') or '—'}, ROCE {fin.get('roce') or '—'}."
        )
    if fin.get("iw_signal") == "more_risk_than_return":
        fin_line.append("El perfil InvestWatch pondera més risc que retorn malgrat el BUY.")
    paragraphs.append(" ".join(fin_line))

    geo_line = []
    if profile.get("policy_link"):
        geo_line.append(f"Policy×Indústria: {profile['policy_link']}.")
    if profile.get("beneficiary_rationale"):
        geo_line.append(profile["beneficiary_rationale"])
    if geo["tense_names"]:
        geo_line.append(
            f"Escenaris adversos del cas ({', '.join(geo['tense_names'])}) poden afectar "
            f"compres públiques, exportacions i timing de contractes."
        )
    if geo.get("dominant_scenario"):
        geo_line.append(
            f"L'escenari Godet més probable és «{geo['dominant_scenario']}»"
            + (f" (~{geo['dominant_prob']}%)" if geo.get("dominant_prob") else "")
            + "."
        )
    actor = geo.get("actor_summary") or {}
    if actor.get("most_likely_scenario"):
        geo_line.append(f"Impacte actors: escenari dominant OSINT «{actor['most_likely_scenario']}».")
    icg_components = geo.get("icg_components") or []
    if geo.get("icg_conf") is not None and icg_components:
        parts = [f"{c.get('label', c.get('name'))} {c.get('value')}%" for c in icg_components[:6]]
        geo_line.append(
            f"Confiança geo-estratègica (ICG) {geo['icg_conf']}%: "
            + ", ".join(parts)
            + "."
        )
    if geo.get("eina_gma") is not None:
        geo_line.append(f"EINA-GMA (atenció geo del cas): {geo['eina_gma']}%.")
    sis = geo.get("sis_score")
    if sis is not None and sis >= 60:
        adj = geo.get("sis_adjustments") or {}
        adj_parts = [f"{k} {v:+d} pp" for k, v in list(adj.items())[:4]]
        geo_line.append(
            f"Sancions (SIS {sis}/100): pressió sobre escenaris"
            + (f" ({', '.join(adj_parts)})" if adj_parts else "")
            + " — informatiu, no reescriu Godet."
        )
        impacts = geo.get("sis_entity_impacts") or []
        if impacts:
            top = ", ".join(
                f"{e.get('entity')} ({e.get('score')})" for e in impacts[:3]
            )
            geo_line.append(f"Entitats més exposades: {top}.")
    osint = geo.get("osint_signals") or {}
    if osint.get("avg_geopolitical_risk") is not None:
        geo_line.append(
            f"Correlats del cas: risc geo {osint.get('avg_geopolitical_risk')}/100"
            + (f", hostilitat {float(osint.get('hostility_ratio') or 0):.0%}" if osint.get("hostility_ratio") is not None else "")
            + (f", {osint.get('conflict_events')} conflictes" if osint.get("conflict_events") else "")
            + "."
        )
    paragraphs.append(" ".join(geo_line) or "Sense context geopolític enriquit al cas.")

    bridge = []
    eina_rec = geo.get("eina_rec") or "HOLD"
    ext = fin.get("signal") or "—"
    if ext != "—" and eina_rec and ext != eina_rec:
        bridge.append(
            f"Divergència clau: informe {ext} vs recomanació EINA {eina_rec}"
            + (f" (confiança {geo.get('eina_conf')}%)." if geo.get("eina_conf") else ".")
        )
        bridge.append(
            "Interpretació: el mercat/analistes veuen valor relatiu (BUY/upside), "
            "mentre EINA manté prudència per incertesa geopolítica del cas i traçabilitat OSINT."
            if ext == "BUY" and eina_rec == "HOLD"
            else "Cal contrastar ambdós senyals amb el pipeline de compres i escenaris abans d'operar."
        )
    elif fn.get("blended_return_index") is not None and fn.get("blended_risk_index") is not None:
        bridge.append(
            f"Índex combinat: retorn {fn['blended_return_index']} · risc {fn['blended_risk_index']} "
            f"(blend informe extern + confiança EINA {geo.get('eina_conf') or '—'}%)."
        )
    if divergences:
        bridge.append(divergences[0].get("summary", ""))
    paragraphs.append(" ".join(p for p in bridge if p))

    return {
        "paragraphs": paragraphs,
        "summary": paragraphs[-1] if paragraphs else "",
        "financial_snapshot": fin,
        "geopolitical_snapshot": {
            "policy_link": profile.get("policy_link"),
            "tense_scenarios": geo["tense_names"],
            "eina_recommendation": eina_rec,
            "eina_confidence": geo.get("icg_conf") or geo.get("eina_conf"),
            "icg_confidence": geo.get("icg_conf"),
        },
    }
