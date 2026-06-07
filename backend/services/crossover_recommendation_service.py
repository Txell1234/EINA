"""Tiered crossover recommendations: private, public, industry, and satellite plays."""
from __future__ import annotations

from typing import Any

from services.crossover_analysis_sections import (
    build_geopolitical_financial_synthesis,
    build_industry_implications,
    _peers_for_sectors,
)
from services.financial_document_service import is_valid_company_name
from services.policy_industry_profiles import all_reference_names, ticker_for_company

_TIER_LABELS = {
    "private": "Inversió privada (equity / posició directa)",
    "public": "Exposició sector públic (política, compres, regulació)",
    "industry": "Indústria / sector",
    "satellite": "Satèl·lits (subministradors, partners, cadena)",
}

_ROLE_PRIVATE_WEIGHT = {
    "prime_contractor": "high",
    "integrator": "high",
    "supplier": "medium",
    "offset_partner": "medium",
    "subcontractor": "low",
    "beneficiary": "medium",
}

_SIGNAL_TO_PRIVATE = {
    "BUY": "ACCUMULATE",
    "HOLD": "HOLD",
    "SELL": "REDUCE",
    "REDUCE_OR_HOLD": "REDUCE",
    "MONITOR": "MONITOR",
    "REVIEW_POSITIVE": "REVIEW_BUY",
}

_SOURCE_LABELS: dict[str, str] = {
    "informe_extern": "Informe extern",
    "informe_extern+eina_entity": "Informe + entitat EINA",
    "eina_policy_link": "Policy×Indústria",
    "eina_roles": "Rol al mapa industrial",
    "eina_scenarios": "Escenaris Godet",
    "eina_sectors": "Sectors de l'entitat",
    "contractor_relationship": "Relació contractual",
    "registry_sector_peer": "Registre del cas",
    "eina_report_link": "Vinculació informe",
    "eina_synthesis": "Síntesi EINA",
    "eina_investments": "Inversions EINA",
    "eina_policy_industry": "Policy×Indústria",
    "llm_narrative": "Narrativa IA",
    "parser": "Parser",
}

_ACTION_JUSTIFICATION: dict[str, str] = {
    "ACCUMULATE": "Informe extern positiu (BUY); té sentit augmentar o obrir posició.",
    "HOLD": "Informe extern neutre (HOLD); mantenir exposició sense canvis.",
    "REDUCE": "Informe extern negatiu; reduir o tancar posició.",
    "MONITOR": "Dades limitades; observar abans d'operar.",
    "REVIEW_BUY": "Mètriques positives però sense senyal fort; revisar abans de comprar.",
    "BUY": "Línia Recommendation/Rating de l'informe indica BUY.",
    "SELL": "Línia Recommendation/Rating de l'informe indica SELL.",
    "REDUCE_OR_HOLD": "InvestWatch pondera més risc que retorn.",
    "REVIEW": "Informe i recomanació EINA del cas no coincideixen.",
    "REVIEW_POSITIVE": "Mètriques clau positives; contrastar amb el cas abans d'actuar.",
    "CONTEXT_OK": "L'informe queda vinculat a una entitat coneguda al mapa EINA.",
    "MONITOR_POLICY": "Seguiment continu per exposició a política pública del cas.",
    "RE-PASTE": "Parser insuficient; cal text PRAAMS amb puntuacions 1-7.",
    "POLICY_ALIGNED": "La política pública analitzada al cas afavoreix aquesta entitat.",
    "POLICY_CAUTION": "Senyal extern feble davant riscos de política pública.",
    "WATCH_PROCUREMENT": "Entitat exposada a compres o programes públics del cas.",
    "PROCUREMENT_RISK": "Senyal extern negatiu; risc al pipeline de compres públiques.",
    "REGULATORY_MONITOR": "Escenaris de tensió del cas poden afectar compres i exportacions.",
    "SECTOR_OVERWEIGHT": "Senyal BUY; el sector té vent favorable via l'entitat focus.",
    "SECTOR_NEUTRAL": "Senyal neutre; sense canvi de ponderació sectorial.",
    "SECTOR_UNDERWEIGHT": "Senyal SELL; reduir pes del sector al portfoli.",
    "MONITOR_PARTNER": "Partner de cadena correlacionat amb l'entitat focus.",
    "SUPPLY_CHAIN_WATCH": "Subministrador del mateix cluster; efecte indirecte probable.",
    "SUPPLY_CHAIN_CAUTION": "Senyal feble al focus; precaució a la cadena de valor.",
    "ALIGN_WITH_SCENARIO": "Parser extern limitat; alinea la decisió amb l'escenari Godet dominant.",
}


def _justification_for_rec(rec: dict[str, Any]) -> str:
    """One-line Catalan justification derived from action + context."""
    action = str(rec.get("action") or "")
    base = _ACTION_JUSTIFICATION.get(action)
    if base:
        return base
    because = (rec.get("because") or "").strip()
    if because:
        words = because.split()
        brief = " ".join(words[:18])
        if len(words) > 18:
            brief += "…"
        return brief
    return "Derivat del creuament informe extern amb context EINA del cas."


def _enrich_recommendation(rec: dict[str, Any]) -> dict[str, Any]:
    out = dict(rec)
    out["justification"] = _justification_for_rec(out)
    src = str(out.get("source") or "")
    out["source_label"] = _SOURCE_LABELS.get(src, src.replace("_", " ").title() or "Regles EINA")
    return out


def _enrich_list(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_enrich_recommendation(r) for r in items]


def _external_signal(metrics: dict[str, Any]) -> str:
    rec = (metrics.get("primary_recommendation") or metrics.get("derived_signal") or "").upper()
    if rec in ("BUY", "HOLD", "SELL"):
        return rec
    iw = metrics.get("investwatch_summary") or {}
    if iw.get("signal") == "more_return_than_risk":
        return "BUY"
    if iw.get("signal") == "more_risk_than_return":
        return "HOLD"
    return "MONITOR"


def _confidence_from_signal(signal: str, iw: dict[str, Any]) -> str:
    if signal in ("BUY", "SELL"):
        return "high"
    avg_ret = iw.get("avg_return_score")
    avg_risk = iw.get("avg_risk_score")
    if isinstance(avg_ret, (int, float)) and isinstance(avg_risk, (int, float)):
        if abs(float(avg_ret) - float(avg_risk)) >= 1.5:
            return "medium"
    return "low"


def _lookup_profile(name: str) -> dict[str, Any] | None:
    from services.actor_impact_utils import canonical_actor

    key = canonical_actor(name).lower()
    if not key:
        return None
    index = all_reference_names()
    for prof_key, prof in index.items():
        if prof_key == key or key in prof_key or prof_key in key:
            return prof
    return None


def _merge_entity_profile(
    entity_name: str | None,
    report_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not entity_name:
        return None
    ctx = report_context or {}
    eina_link = ctx.get("eina_link") or {}
    ref_profile = _lookup_profile(entity_name) or {}
    return {
        "name": eina_link.get("name") or entity_name,
        "ticker": ref_profile.get("ticker") or ticker_for_company(entity_name),
        "country": eina_link.get("country") or ref_profile.get("country"),
        "region": eina_link.get("region") or ref_profile.get("region"),
        "roles": list(eina_link.get("roles") or ref_profile.get("roles") or []),
        "sectors": list(eina_link.get("sectors") or ref_profile.get("sectors") or []),
        "policy_link": eina_link.get("policy_link") or ref_profile.get("policy_link") or "",
        "beneficiary_rationale": (
            eina_link.get("beneficiary_rationale") or ref_profile.get("beneficiary_rationale") or ""
        ),
        "contractor_relationships": list(
            eina_link.get("contractor_relationships")
            or ref_profile.get("contractor_relationships")
            or []
        ),
        "registry_found": bool(eina_link.get("found")),
    }


def _private_recommendations(
    profile: dict[str, Any],
    *,
    signal: str,
    iw: dict[str, Any],
    metrics: dict[str, Any],
    eina: dict[str, Any],
    final_numbers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    name = profile["name"]
    action = _SIGNAL_TO_PRIVATE.get(signal, "MONITOR")
    roles = profile.get("roles") or []
    weight = "medium"
    for role in roles:
        weight = _ROLE_PRIVATE_WEIGHT.get(role, weight)
        if weight == "high":
            break

    because_parts = [
        f"Senyal informe extern: {signal}.",
        f"Acció privada suggerida per {name}.",
    ]
    if profile.get("beneficiary_rationale"):
        because_parts.append(profile["beneficiary_rationale"][:180])
    if iw.get("avg_return_score") is not None:
        because_parts.append(
            f"InvestWatch retorn {iw['avg_return_score']}/7 vs risc {iw.get('avg_risk_score')}/7."
        )
    if metrics.get("upside_consensus_pct") is not None:
        because_parts.append(f"Upside consens {metrics['upside_consensus_pct']}%.")
    km = metrics.get("key_metrics") or []
    roa = next((m for m in km if str(m.get("label", "")).upper() == "ROA"), None)
    roce = next((m for m in km if str(m.get("label", "")).upper() == "ROCE"), None)
    if roa or roce:
        because_parts.append(
            "Ratios: "
            + ", ".join(
                f"{m['label']} {m['value_pct']}%"
                for m in [roa, roce]
                if m
            )
        )
    fn = final_numbers or {}
    if fn.get("blended_return_index") is not None:
        because_parts.append(
            f"Blend EINA retorn {fn['blended_return_index']} · risc {fn.get('blended_risk_index', '—')}."
        )
    inv_recs = eina.get("investment_recommendations") or []
    if inv_recs:
        because_parts.append(
            f"EINA cas: {inv_recs[0].get('type', 'HOLD')} "
            f"(conf. {inv_recs[0].get('confidence_pct', '—')}%)."
        )
    elif metrics.get("key_metrics"):
        km2 = metrics["key_metrics"][:2]
        because_parts.append(
            "Mètriques: " + ", ".join(f"{m['label']} {m['value_pct']}%" for m in km2)
        )

    geo_note = ""
    scenarios = eina.get("scenarios") or []
    tense = [s for s in scenarios if (s.get("type") or "").lower() in ("inferno", "tension", "infern", "tensio")]
    if tense and signal == "BUY":
        geo_note = (
            f" Atenció geo: {', '.join(s.get('name', '?') for s in tense[:2])} "
            f"justifica prudència EINA malgrat BUY extern."
        )

    return [
        {
            "tier": "private",
            "tier_label": _TIER_LABELS["private"],
            "action": action,
            "target": name,
            "ticker": profile.get("ticker"),
            "horizon": "6-18 mesos",
            "confidence": _confidence_from_signal(signal, iw),
            "weight": weight,
            "because": " ".join(because_parts) + geo_note,
            "source": "informe_extern+eina_entity",
        }
    ]


def _public_recommendations(
    profile: dict[str, Any],
    *,
    signal: str,
    eina: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    name = profile["name"]
    policy = (profile.get("policy_link") or "").strip()
    roles = profile.get("roles") or []

    if policy:
        action = "POLICY_ALIGNED" if signal in ("BUY", "HOLD") else "POLICY_CAUTION"
        out.append(
            {
                "tier": "public",
                "tier_label": _TIER_LABELS["public"],
                "action": action,
                "target": f"Política pública · {name}",
                "ticker": None,
                "horizon": "3-12 mesos",
                "confidence": "medium" if profile.get("registry_found") else "low",
                "weight": "high" if "prime_contractor" in roles else "medium",
                "because": (
                    f"Exposició a política/defensa pública vinculada a {name}: {policy[:220]}"
                ),
                "source": "eina_policy_link",
            }
        )

    if any(r in roles for r in ("prime_contractor", "integrator", "beneficiary")):
        proc_action = "WATCH_PROCUREMENT" if signal != "SELL" else "PROCUREMENT_RISK"
        out.append(
            {
                "tier": "public",
                "tier_label": _TIER_LABELS["public"],
                "action": proc_action,
                "target": f"Compres públiques · {name}",
                "ticker": None,
                "horizon": "12-24 mesos",
                "confidence": "medium",
                "weight": "high" if "prime_contractor" in roles else "medium",
                "because": (
                    f"{name} actua com a {'prime' if 'prime_contractor' in roles else 'integrador/beneficiari'} "
                    f"en compres de defensa o programes públics del cas analitzat."
                ),
                "source": "eina_roles",
            }
        )

    scenarios = eina.get("scenarios") or []
    tense = [s for s in scenarios if (s.get("type") or "").lower() in ("inferno", "tension", "infern", "tensio")]
    if tense and policy:
        tense_names = ", ".join(s.get("name", "?") for s in tense[:2])
        out.append(
            {
                "tier": "public",
                "tier_label": _TIER_LABELS["public"],
                "action": "REGULATORY_MONITOR",
                "target": f"Risc geopolític · {profile.get('country', 'regió')}",
                "ticker": None,
                "horizon": "Continu",
                "confidence": "medium",
                "weight": "medium",
                "because": (
                    f"Escenaris de tensió al cas ({tense_names}) poden afectar compres públiques "
                    f"i exportacions vinculades a {name}."
                ),
                "source": "eina_scenarios",
            }
        )

    return out[:3]


def _industry_recommendations(
    profile: dict[str, Any],
    *,
    signal: str,
    registry_companies: list[dict[str, Any]] | None = None,
    industry_implications: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    sectors = profile.get("sectors") or []
    if not sectors:
        return []

    impl_by_sector = {i["sector"]: i for i in (industry_implications or [])}

    sector_action = (
        "SECTOR_OVERWEIGHT"
        if signal == "BUY"
        else "SECTOR_UNDERWEIGHT"
        if signal == "SELL"
        else "SECTOR_NEUTRAL"
    )
    out: list[dict[str, Any]] = []

    for sector in sectors[:4]:
        impl = impl_by_sector.get(sector) or {}
        peers: list[str] = list(impl.get("peers") or [])
        for co in registry_companies or []:
            if co.get("name") == profile.get("name"):
                continue
            if sector in (co.get("sectors") or []):
                pn = co.get("name", "")
                if pn and pn not in peers:
                    peers.append(pn)
        peer_note = f" Peers al cas: {', '.join(peers[:4])}." if peers else ""

        because = (
            f"Sector {sector} exposat via {profile['name']} (senyal extern {signal})."
            f"{peer_note}"
        )
        if impl.get("financial_read"):
            because += f" Finances: {impl['financial_read']}."
        if impl.get("geopolitical_read"):
            because += f" Geo: {impl['geopolitical_read'][:220]}."

        out.append(
            {
                "tier": "industry",
                "tier_label": _TIER_LABELS["industry"],
                "action": sector_action,
                "target": sector.replace("_", " ").title(),
                "ticker": None,
                "horizon": "12-36 mesos",
                "confidence": "medium" if signal in ("BUY", "SELL") else "low",
                "weight": "medium",
                "because": because.strip(),
                "implication": impl.get("implication"),
                "financial_read": impl.get("financial_read"),
                "geopolitical_read": impl.get("geopolitical_read"),
                "suggested_play": impl.get("suggested_play"),
                "source": "eina_sectors",
            }
        )
    return out


def _satellite_recommendations(
    profile: dict[str, Any],
    *,
    signal: str,
    registry_companies: list[dict[str, Any]] | None = None,
    metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    focus = profile.get("name") or ""
    rels = profile.get("contractor_relationships") or []

    sat_action = (
        "MONITOR_PARTNER"
        if signal in ("BUY", "HOLD", "MONITOR")
        else "SUPPLY_CHAIN_CAUTION"
    )

    for rel in rels[:4]:
        partner = rel.get("partner") or ""
        if not partner:
            continue
        rel_type = rel.get("type") or "partner"
        ticker = ticker_for_company(partner)
        because = (
            f"Satèl·lit de {focus}: relació {rel_type} ({rel.get('region', '—')}). "
            f"Moviment en {focus} ({signal}) sovint arrossega partners de cadena."
        )
        if metrics and metrics.get("upside_consensus_pct") is not None and signal == "BUY":
            because += f" Upside focus {metrics['upside_consensus_pct']}% → correlació indirecta probable."
        out.append(
            {
                "tier": "satellite",
                "tier_label": _TIER_LABELS["satellite"],
                "action": sat_action,
                "target": partner,
                "ticker": ticker,
                "horizon": "6-18 mesos",
                "confidence": "medium",
                "weight": "medium",
                "because": because,
                "relationship_type": rel_type,
                "source": "contractor_relationship",
            }
        )

    sectors = set(profile.get("sectors") or [])
    for co in registry_companies or []:
        if co.get("name") == focus:
            continue
        roles = co.get("roles") or []
        if "supplier" not in roles and "integrator" not in roles:
            continue
        if not sectors.intersection(co.get("sectors") or []):
            continue
        if any(r["target"] == co.get("name") for r in out):
            continue
        out.append(
            {
                "tier": "satellite",
                "tier_label": _TIER_LABELS["satellite"],
                "action": "SUPPLY_CHAIN_WATCH",
                "target": co.get("name", ""),
                "ticker": co.get("ticker") or ticker_for_company(co.get("name", "")),
                "horizon": "6-12 mesos",
                "confidence": "low",
                "weight": "low",
                "because": (
                    f"Subministrador/integrador al mateix cluster sectorial que {focus} "
                    f"({', '.join(sorted(sectors)[:3])}). "
                    f"{(co.get('beneficiary_rationale') or '')[:120]}"
                ).strip(),
                "source": "registry_sector_peer",
            }
        )
        if len(out) >= 6:
            break

    # Reference-profile peers (IHI, MELCO, etc.) when registry is sparse
    if len(out) < 4:
        for peer in _peers_for_sectors(list(sectors), focus):
            if any(r["target"] == peer["name"] for r in out):
                continue
            role_hint = ", ".join(peer.get("roles") or []) or "peer"
            out.append(
                {
                    "tier": "satellite",
                    "tier_label": _TIER_LABELS["satellite"],
                    "action": "SUPPLY_CHAIN_WATCH" if signal != "SELL" else "SUPPLY_CHAIN_CAUTION",
                    "target": peer["name"],
                    "ticker": peer.get("ticker"),
                    "horizon": "6-18 mesos",
                    "confidence": "low",
                    "weight": "low",
                    "because": (
                        f"Peer/satèl·lit del cluster ({role_hint}) vinculat a {focus} via "
                        f"sectors {', '.join(peer.get('sectors') or [])}. "
                        f"{peer.get('beneficiary_rationale') or peer.get('policy_link') or ''}"
                    ).strip(),
                    "source": "registry_sector_peer",
                }
            )
            if len(out) >= 6:
                break

    return out[:6]


def build_tiered_recommendations(
    metrics: dict[str, Any],
    eina: dict[str, Any],
    *,
    entity_name: str | None = None,
    report_context: dict[str, Any] | None = None,
    registry_companies: list[dict[str, Any]] | None = None,
    final_numbers: dict[str, Any] | None = None,
    divergences: list[dict[str, Any]] | None = None,
    alignments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Rule-based recommendations across private, public, industry, and satellite layers.
    No LLM — uses parsed report signal + entity profile + case registry.
    """
    focus = (
        entity_name
        or (report_context or {}).get("reference_entity")
        or (report_context or {}).get("resolved_company")
        or metrics.get("reference_entity")
    )
    if not focus:
        cn = metrics.get("company_name")
        if cn and is_valid_company_name(cn):
            focus = cn
    profile = _merge_entity_profile(focus, report_context)
    signal = _external_signal(metrics)
    iw = metrics.get("investwatch_summary") or {}

    empty: dict[str, Any] = {
        "focus_entity": focus,
        "external_signal": signal,
        "tier_labels": _TIER_LABELS,
        "private": [],
        "public": [],
        "industries": [],
        "satellites": [],
        "summary": "Selecciona una empresa o actor de referència per obtenir recomanacions per capes.",
    }

    if not profile:
        empty["summary"] = (
            "Sense entitat vinculada — vincula l'informe a una empresa o actor del registre "
            "per recomanacions privades, públiques, sectorials i satèl·lits."
        )
        return empty

    industry_implications = build_industry_implications(
        profile, metrics, eina, signal=signal, final_numbers=final_numbers
    )
    geo_fin = build_geopolitical_financial_synthesis(
        profile,
        metrics,
        eina,
        final_numbers=final_numbers,
        divergences=divergences,
        alignments=alignments,
    )

    private = _enrich_list(
        _private_recommendations(
            profile, signal=signal, iw=iw, metrics=metrics, eina=eina, final_numbers=final_numbers
        )
    )
    public = _enrich_list(_public_recommendations(profile, signal=signal, eina=eina))
    industries = _enrich_list(
        _industry_recommendations(
            profile,
            signal=signal,
            registry_companies=registry_companies,
            industry_implications=industry_implications,
        )
    )
    satellites = _enrich_list(
        _satellite_recommendations(
            profile, signal=signal, registry_companies=registry_companies, metrics=metrics
        )
    )

    parts = [f"Senyal extern {signal} sobre {profile['name']}."]
    if private:
        parts.append(f"Privat: {private[0]['action']}.")
    if public:
        parts.append(f"Públic: {len(public)} línies d'exposició.")
    if industries:
        parts.append(f"Sectors: {len(industries)}.")
    if satellites:
        parts.append(f"Satèl·lits: {len(satellites)}.")

    return {
        "focus_entity": profile["name"],
        "external_signal": signal,
        "tier_labels": _TIER_LABELS,
        "entity_profile": profile,
        "private": private,
        "public": public,
        "industries": industries,
        "satellites": satellites,
        "industry_implications": industry_implications,
        "geopolitical_financial_synthesis": geo_fin,
        "summary": " ".join(parts),
    }
