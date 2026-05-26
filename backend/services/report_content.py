"""Contingut enriquit per informes: resum executiu, perfils de variables i factors clau."""
from __future__ import annotations

from typing import Any, Optional

from services.report_i18n import ReportStrings, get_report_strings


def _var_type_label(var_type: str, s: ReportStrings) -> str:
    t = (var_type or "I").upper()
    if t == "E":
        return s.var_type_e
    if t == "M":
        return s.var_type_m
    return s.var_type_i


def _sector_map(micmac: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not micmac or not micmac.sectors:
        return out
    sectors = micmac.sectors if isinstance(micmac.sectors, list) else []
    mot = micmac.motricite_direct if isinstance(micmac.motricite_direct, list) else []
    dep = micmac.dependence_direct if isinstance(micmac.dependence_direct, list) else []
    for i, sec in enumerate(sectors):
        if not isinstance(sec, dict):
            continue
        code = str(sec.get("code") or "")
        if not code:
            continue
        out[code] = {
            "sector": sec.get("sector") or sec.get("sector_name") or "—",
            "motricity": mot[i] if i < len(mot) else sec.get("motricite"),
            "dependence": dep[i] if i < len(dep) else sec.get("dependencia"),
            "index": i,
        }
    return out


def _suggested_rationale(code: str, suggested: list[dict]) -> str:
    for sv in suggested:
        if str(sv.get("code", "")).upper() == code.upper():
            return str(sv.get("rationale") or sv.get("desc") or "").strip()
    return ""


def _relations_for_var(
    code: str,
    var_index: int,
    suggestions: dict | None,
    vars_list: list,
) -> list[str]:
    if not suggestions:
        return []
    rels: list[str] = []
    for item in suggestions.get("suggestions") or []:
        row_i, col_i = item.get("row"), item.get("col")
        if row_i != var_index and col_i != var_index:
            continue
        other_i = col_i if row_i == var_index else row_i
        other_code = (
            vars_list[other_i].code
            if isinstance(other_i, int) and 0 <= other_i < len(vars_list)
            else str(other_i)
        )
        reason = item.get("reason") or ""
        val = item.get("value", "")
        rels.append(f"{code} ↔ {other_code} ({val}): {reason}".strip())
    return rels[:6]


def _evidence_for_var(name: str, code: str, bundle: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    needle = (name or code or "").lower()
    if not needle:
        return hits
    retro = bundle.get("retrospective") or {}
    for pair in (retro.get("micmac_evidence") or {}).get("pairs") or []:
        from_t = str(pair.get("from_topic", "")).lower()
        to_t = str(pair.get("to_topic", "")).lower()
        if needle in from_t or needle in to_t or code.lower() in from_t or code.lower() in to_t:
            hits.append(
                f"{pair.get('from_topic')} → {pair.get('to_topic')} "
                f"({pair.get('n_statements')} decl., conf. {pair.get('confidence')})"
            )
    for stmt in (bundle.get("statements") or [])[:200]:
        topic = (getattr(stmt, "topic", None) or "").lower()
        actor = (getattr(stmt, "actor", None) or "").lower()
        if needle in topic or needle in actor:
            excerpt = (getattr(stmt, "statement", "") or "")[:120]
            url = getattr(stmt, "source_url", "") or ""
            hits.append(f"«{excerpt}…» ({url[:50]})")
        if len(hits) >= 5:
            break
    return hits[:5]


def build_variable_profiles(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    s = get_report_strings(bundle.get("lang"))
    vars_list: list = bundle.get("variables") or []
    micmac = bundle.get("micmac")
    sectors = _sector_map(micmac)
    suggested = bundle.get("suggested_variables") or []
    suggestions = bundle.get("micmac_suggestions")

    profiles: list[dict[str, Any]] = []
    for i, v in enumerate(vars_list):
        code = str(v.code)
        sec = sectors.get(code, {})
        osint_rat = _suggested_rationale(code, suggested)
        relations = _relations_for_var(code, i, suggestions, vars_list)
        evidence = _evidence_for_var(v.name, code, bundle)

        motivation_parts: list[str] = []
        if v.description:
            motivation_parts.append(str(v.description))
        if osint_rat and osint_rat not in motivation_parts:
            motivation_parts.append(osint_rat)
        if sec.get("sector"):
            motivation_parts.append(
                f"{s.var_sector}: {sec.get('sector')}. "
                f"{s.var_motricity}: {sec.get('motricity', '—')}; "
                f"{s.var_dependence}: {sec.get('dependence', '—')}."
            )
        if relations:
            motivation_parts.append(f"{s.var_relations}: " + "; ".join(relations[:3]))

        profiles.append(
            {
                "code": code,
                "name": v.name,
                "var_type": v.var_type or "I",
                "type_label": _var_type_label(v.var_type or "I", s),
                "description": v.description or "",
                "osint_rationale": osint_rat,
                "sector": sec.get("sector"),
                "motricity": sec.get("motricity"),
                "dependence": sec.get("dependence"),
                "relations": relations,
                "evidence": evidence,
                "motivation": " ".join(motivation_parts).strip(),
            }
        )
    return profiles


def build_key_factors(bundle: dict[str, Any]) -> list[dict[str, str]]:
    factors: list[dict[str, str]] = []
    impact = bundle.get("actor_impact") or {}
    inv = bundle.get("investment") or {}

    for j in (impact.get("scenario_justifications") or [])[:4]:
        factors.append(
            {
                "factor": j.get("scenario_name") or "Escenari",
                "detail": j.get("rationale") or "",
                "source": "MIC-MAC / OSINT",
            }
        )

    for risk in (inv.get("risks") or [])[:5]:
        rf = risk.get("factors") or []
        detail = risk.get("description") or ""
        if rf:
            detail = f"{detail} · Factors: {', '.join(str(x) for x in rf[:4])}"
        factors.append(
            {
                "factor": risk.get("risk_type") or "Risc",
                "detail": detail,
                "source": "Anàlisi d'inversió",
            }
        )

    for c in (impact.get("claims") or [])[:5]:
        factors.append(
            {
                "factor": (c.get("scenario_name") or "Impacte")[:60],
                "detail": c.get("claim") or "",
                "source": "Impacte actors",
            }
        )

    profiles = bundle.get("variable_profiles") or build_variable_profiles(bundle)
    for p in sorted(
        profiles,
        key=lambda x: float(x.get("motricity") or 0) if x.get("motricity") is not None else 0,
        reverse=True,
    )[:4]:
        if p.get("motricity") is not None:
            factors.append(
                {
                    "factor": f"{p['code']} · {p['name']}",
                    "detail": p.get("motivation") or p.get("description") or "",
                    "source": "MIC-MAC",
                }
            )
    return factors[:12]


def build_executive_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    s = get_report_strings(bundle.get("lang"))
    project = bundle["project"]
    impact = bundle.get("actor_impact") or {}
    inv = bundle.get("investment") or {}
    retro = bundle.get("retrospective") or {}
    scenarios = bundle.get("scenarios") or []
    articles = bundle.get("osint_articles") or []
    statements = bundle.get("statements") or []
    profiles = bundle.get("variable_profiles") or build_variable_profiles(bundle)
    validation = impact.get("validation") or {}

    avg_ground = None
    gs = [float(getattr(st, "grounding_score", 0) or 0) for st in statements if getattr(st, "grounding_score", None)]
    if gs:
        avg_ground = round(sum(gs) / len(gs) * 100, 1)

    summary_impact = impact.get("summary") or {}
    sections: list[dict[str, Any]] = []

    sections.append(
        {
            "title": s.es_objective,
            "paragraphs": [
                f"{s.es_hypothesis}: {project.hypothesis or '—'}",
                f"{s.es_context}: {project.context or '—'}",
            ],
            "bullets": [],
        }
    )

    osint_bullets = [
        f"{len(articles)} {s.articles}",
        f"{len(statements)} {s.statements}",
    ]
    if retro.get("has_data"):
        osint_bullets.append(
            f"Retrospectiva: {retro.get('total_statements', 0)} declaracions "
            f"({retro.get('date_range', '—')})"
        )
    if avg_ground is not None:
        osint_bullets.append(f"Grounding mitjà extracció: {avg_ground}%")
    sections.append({"title": s.es_osint, "paragraphs": [], "bullets": osint_bullets})

    var_bullets = []
    for p in profiles[:6]:
        line = f"{p['code']} — {p['name']} ({p['var_type']})"
        if p.get("sector"):
            line += f" · {p['sector']}"
        if p.get("motricity") is not None:
            line += f" · motricitat {p['motricity']}"
        if p.get("motivation"):
            line += f". {p['motivation'][:180]}"
        var_bullets.append(line)
    if not var_bullets:
        var_bullets = [s.no_data]
    sections.append({"title": s.es_variables, "paragraphs": [], "bullets": var_bullets})

    scen_bullets = []
    for sc in scenarios:
        poss = getattr(sc, "possibility", None) or "PLAUSIBLE"
        scen_bullets.append(
            f"{sc.name} ({sc.scenario_type or '—'}): "
            f"{s.possibility} {poss} · {s.probability} {sc.probability or '—'}"
        )
    if summary_impact.get("most_likely_scenario"):
        scen_bullets.insert(
            0,
            f"{s.most_likely}: {summary_impact['most_likely_scenario']}",
        )
    if not scen_bullets:
        scen_bullets = [s.no_data]
    sections.append({"title": s.es_scenarios, "paragraphs": [], "bullets": scen_bullets})

    actor_bullets = []
    if impact.get("has_data"):
        actor_bullets.append(
            f"{summary_impact.get('actor_count', 0)} actors · "
            f"{summary_impact.get('claim_count', 0)} conclusions · "
            f"confiança {summary_impact.get('overall_confidence', '—')}%"
        )
        for c in (impact.get("claims") or [])[:4]:
            actor_bullets.append(f"{c.get('claim', '')[:200]} (conf. {c.get('confidence', '—')}%)")
    else:
        actor_bullets = [s.no_data]
    sections.append({"title": s.es_actors, "paragraphs": [], "bullets": actor_bullets})

    risk_bullets = []
    for risk in (inv.get("risks") or [])[:4]:
        risk_bullets.append(
            f"{risk.get('risk_type')} ({risk.get('risk_level')}): "
            f"{(risk.get('description') or '')[:160]}"
        )
    for opp in (inv.get("opportunities") or [])[:3]:
        risk_bullets.append(f"Oportunitat: {opp.get('title')} — {(opp.get('description') or '')[:120]}")
    if not risk_bullets:
        risk_bullets = [s.no_data]
    sections.append({"title": s.es_risks, "paragraphs": [], "bullets": risk_bullets})

    concl_bullets = []
    for c in (impact.get("claims") or [])[:6]:
        concl_bullets.append(c.get("claim") or "")
    for rec in (inv.get("recommendations") or [])[:2]:
        concl_bullets.append(f"Recomanació {rec.get('type')}: {(rec.get('rationale') or '')[:160]}")
    if not concl_bullets:
        concl_bullets = [project.hypothesis or s.no_data]
    sections.append({"title": s.es_conclusions, "paragraphs": [], "bullets": concl_bullets})

    limit_paragraphs = []
    if validation and not validation.get("export_ready"):
        limit_paragraphs.append(
            f"{s.traceability_warning} "
            f"({validation.get('claims_without_citation', 0)} sense citació)."
        )
    errors = bundle.get("osint_query_errors") or []
    if errors:
        limit_paragraphs.append(f"{len(errors)} consulta(s) OSINT amb errors de recollida.")
    if not limit_paragraphs:
        limit_paragraphs = ["Dades OSINT, MIC-MAC i escenaris coherents amb el pipeline executat."]
    sections.append({"title": s.es_limitations, "paragraphs": limit_paragraphs, "bullets": []})

    return {
        "sections": sections,
        "key_factors": build_key_factors(bundle),
        "profiles_count": len(profiles),
    }
