"""Unified geo-intelligence layer — ICG bundle, synthesis, case context (sync + async paths)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.external_report import CaseExternalReport
from services.actor_impact_service import ActorImpactService
from services.actor_impact_utils import canonical_actor
from services.company_registry_service import load_company_registry
from services.financial_crossover_service import FinancialCrossoverService
from services.geopolitical_confidence import build_geopolitical_confidence_bundle


def _registry_row_for_company(
    registry: dict[str, Any],
    focus_company: str,
) -> dict[str, Any] | None:
    key = canonical_actor(focus_company).lower()
    if not key:
        return None
    for row in registry.get("companies") or []:
        name = canonical_actor(str(row.get("name") or "")).lower()
        if name == key or key in name or name in key:
            return row
    return None


async def _external_metrics_for_entity(
    db: AsyncSession,
    case_id: int,
    focus_company: str,
) -> dict[str, Any] | None:
    key = canonical_actor(focus_company).lower()
    if not key:
        return None
    r = await db.execute(
        select(CaseExternalReport)
        .where(CaseExternalReport.case_id == case_id)
        .order_by(CaseExternalReport.created_at.desc())
        .limit(20)
    )
    for report in r.scalars().all():
        metrics = report.parsed_metrics if isinstance(report.parsed_metrics, dict) else {}
        ref = canonical_actor(str(metrics.get("reference_entity") or metrics.get("company_name") or "")).lower()
        if ref and (key in ref or ref in key):
            return metrics
    return None


def _component_map(components: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(c.get("name")): c for c in components if c.get("name")}


def derive_driver_interactions(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Rule-based pairwise insights (no ML). Mirrors the intent of SHAP interactions
    using case ICG components and sanction context.
    """
    components = bundle.get("geopolitical_confidence_components") or bundle.get("components") or []
    by_name = _component_map(components)
    gpr = bundle.get("gpr_case_level")
    sis = bundle.get("sanction_impact_score")
    interactions: list[dict[str, Any]] = []

    geo = by_name.get("geopolitical_risk_environment")
    trace = by_name.get("osint_traceability")
    scen = by_name.get("scenario_outlook")
    gma = by_name.get("eina_gma")

    if geo and trace and float(geo["value"]) < 45 and float(trace["value"]) >= 70:
        interactions.append(
            {
                "pair": "geo_risk × osint_traceability",
                "direction": "tension",
                "score": round((100 - float(geo["value"])) * 0.4, 1),
                "because": (
                    "Entorn geo advers però evidència OSINT sòlida — confiança analítica parcialment compensada."
                ),
            }
        )
    if geo and scen and float(geo["value"]) < 50 and float(scen["value"]) < 55:
        interactions.append(
            {
                "pair": "geo_risk × scenario_outlook",
                "direction": "negative",
                "score": round((100 - float(geo["value"])) * 0.35, 1),
                "because": "Risc entorn baix i escenaris tensió/conflicte pesats — ICG penalitzat.",
            }
        )
    if gma and geo and float(gma["value"]) >= 65 and float(geo["value"]) < 50:
        interactions.append(
            {
                "pair": "GMA × geo_risk",
                "direction": "attention_spike",
                "score": round(float(gma["value"]) * 0.25, 1),
                "because": (
                    "Alta atenció de mercat (EINA-GMA) amb entorn geo advers — senyal de preu de risc elevat."
                ),
            }
        )
    if sis and sis >= 60 and geo:
        interactions.append(
            {
                "pair": "sanctions × geo_risk",
                "direction": "negative",
                "score": round(float(sis) * 0.3, 1),
                "because": f"SIS {sis:.0f} reforça penalització del component d'entorn geo.",
            }
        )
    if gpr is not None and float(gpr) >= 70 and geo:
        interactions.append(
            {
                "pair": "GPR_cas × geo_risk",
                "direction": "multiplier",
                "score": round(float(bundle.get("gpr_multiplier_applied") or 1) * 10, 1),
                "because": (
                    f"GPR cas {float(gpr):.1f} → multiplicador sigmoid "
                    f"{float(bundle.get('gpr_multiplier_applied') or 1):.2f} al pes del risc entorn."
                ),
            }
        )
    return sorted(interactions, key=lambda x: x["score"], reverse=True)[:6]


def build_executive_synthesis_markdown(
    bundle: dict[str, Any],
    *,
    case_name: str | None = None,
    analytics: dict[str, Any] | None = None,
) -> str:
    """Deterministic executive synthesis — traceable, no LLM."""
    title = case_name or "Cas prospectiu"
    icg = bundle.get("geopolitical_confidence_index")
    source = bundle.get("confidence_source") or "missing"
    posture = bundle.get("investment_posture") or {}
    components = bundle.get("geopolitical_confidence_components") or []
    interactions = derive_driver_interactions(bundle)
    sis = bundle.get("sanction_impact_score")
    gma = bundle.get("eina_gma")

    lines: list[str] = [
        f"# Síntesi Geo-Financera — {title}",
        "",
    ]
    if icg is not None:
        lines.append(f"**Confiança geo-estratègica (ICG):** **{icg:.1f}%** (`{source}`)")
    else:
        lines.append("**Confiança geo-estratègica:** *pendent* — executa el pipeline d'intel·ligència al cas.")
    lines.append("")
    if bundle.get("confidence_detail"):
        lines.append(f"> {bundle['confidence_detail']}")
        lines.append("")

    if components:
        lines.extend(["## Desglossament ICG", ""])
        lines.append("| Component | Valor | Pes | Justificació |")
        lines.append("|-----------|-------|-----|--------------|")
        for c in components:
            w = c.get("weight") or c.get("base_weight") or 0
            lines.append(
                f"| {c.get('label', c.get('name'))} | {c.get('value')}% | "
                f"{float(w) * 100:.0f}% | {c.get('because', '')} |"
            )
        lines.append("")

    if gma is not None:
        lines.extend(
            [
                "## Atenció mercat (EINA-GMA)",
                "",
                f"**GMA:** {gma:.1f}% — inspirat en lògica BGRI però 100% case-specific.",
            ]
        )
        if bundle.get("eina_gma_formula"):
            lines.append(f"*{bundle['eina_gma_formula']}*")
        lines.append("")

    if sis is not None:
        lines.extend([f"## Impacte sancions (SIS): **{sis:.0f}/100**", ""])
        for d in (bundle.get("sanction_drivers") or [])[:5]:
            excerpt = d.get("excerpt") or d.get("keyword") or d.get("type") or ""
            lines.append(f"- {d.get('type', 'driver')}: {excerpt}")
        ents = bundle.get("sanction_entity_impacts") or []
        if ents:
            lines.append("")
            lines.append("| Entitat | Score | Δ prob. |")
            lines.append("|---------|-------|---------|")
            for e in ents[:6]:
                lines.append(
                    f"| {e.get('entity')} | {e.get('score')} | {e.get('prob_adjust_pp', 0):+d} pp |"
                )
        adj = bundle.get("sanction_scenario_adjustments") or {}
        if adj:
            lines.append("")
            lines.append("**Ajust escenaris (informatiu):** " + ", ".join(f"{k}: {v}%" for k, v in adj.items()))
        lines.append("")

    if interactions:
        lines.extend(["## Interaccions de drivers (regles traçables)", ""])
        for ix in interactions:
            lines.append(f"- **{ix['pair']}** ({ix['direction']}): {ix['because']}")
        lines.append("")

    rec = posture.get("recommendation")
    rec_conf = posture.get("confidence_pct")
    rec_src = posture.get("source")
    if rec:
        lines.extend(
            [
                "## Postura d'inversió (separada de l'ICG)",
                "",
                f"**{rec}** {rec_conf if rec_conf is not None else '—'}%"
                f" (`{rec_src or 'unknown'}`) — no confondre amb confiança geo-estratègica.",
                "",
            ]
        )

    if analytics:
        mc = analytics.get("monte_carlo") or {}
        if mc.get("mean") is not None:
            lines.extend(
                [
                    "## Analytics Lab (última execució)",
                    "",
                    f"Monte Carlo: mitjana **{mc['mean']}%**, P5 {mc.get('p5')}% · P95 {mc.get('p95')}%",
                ]
            )
            tornado = analytics.get("tornado") or []
            if tornado:
                top = tornado[0]
                lines.append(
                    f"Component més sensible: **{top.get('label') or top.get('component')}** "
                    f"(swing {top.get('swing')} pts)."
                )
            lines.append("")

    lines.extend(
        [
            "---",
            "*Generat per EINA GeoIntelligence — determinista, traçable, sense LLM a la síntesi final.*",
        ]
    )
    return "\n".join(lines)


class GeoIntelligenceService:
    """Build ICG bundle and related artifacts for any entry point (crossover, inquiry, API)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_bundle_for_case(
        self,
        case_id: int,
        *,
        focus_company: str | None = None,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        crossover = FinancialCrossoverService(self.db)
        eina = await crossover._eina_metrics(case_id, project_id=project_id, focus_company=focus_company)
        impact: dict[str, Any] = {}
        try:
            impact = await ActorImpactService(self.db).get_latest(case_id) or {}
            if not impact.get("has_data"):
                impact = await ActorImpactService(self.db).build_assessment(
                    case_id, project_id=project_id or eina.get("project_id")
                )
        except Exception:
            impact = eina.get("actor_impact") or {}

        effective_focus = focus_company or eina.get("focus_company")
        registry_row: dict[str, Any] | None = None
        external_metrics: dict[str, Any] | None = None
        if effective_focus:
            registry = await load_company_registry(
                self.db, case_id, project_id=project_id or eina.get("project_id")
            )
            registry_row = _registry_row_for_company(registry, effective_focus)
            external_metrics = await _external_metrics_for_entity(self.db, case_id, effective_focus)

        bundle = build_geopolitical_confidence_bundle(
            impact,
            inv_recs=eina.get("investment_recommendations") or [],
            focus_company=effective_focus,
            entity_focus_match=eina.get("entity_focus_match"),
            policy_rows=eina.get("policy_companies") or [],
            scenarios=eina.get("scenarios") or [],
            registry_row=registry_row,
            external_metrics=external_metrics,
        )
        bundle["driver_interactions"] = derive_driver_interactions(bundle)
        bundle["case_id"] = case_id
        bundle["focus_company"] = effective_focus
        return bundle

    def eina_case_summary_from_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Shape compatible with crossover eina_case_summary."""
        posture = bundle.get("investment_posture") or {}
        entity_posture = bundle.get("entity_investment_posture") or {}
        case_icg = bundle.get("case_icg") or {}
        entity_icg = bundle.get("entity_icg")
        headline_icg = bundle.get("entity_confidence_index") or bundle.get("geopolitical_confidence_index")
        return {
            "investment_recommendation": posture.get("recommendation"),
            "investment_confidence_pct": posture.get("confidence_pct"),
            "investment_rationale": posture.get("rationale"),
            "investment_posture_source": posture.get("source"),
            "entity_investment_recommendation": entity_posture.get("recommendation"),
            "entity_investment_confidence_pct": entity_posture.get("confidence_pct"),
            "entity_investment_rationale": entity_posture.get("rationale"),
            "entity_investment_posture_source": entity_posture.get("source"),
            "geopolitical_confidence_index": bundle.get("geopolitical_confidence_index"),
            "case_geopolitical_confidence_index": bundle.get("case_geopolitical_confidence_index")
            or case_icg.get("index"),
            "entity_confidence_index": bundle.get("entity_confidence_index"),
            "entity_icg_delta": bundle.get("entity_icg_delta"),
            "focus_company": bundle.get("focus_company"),
            "case_icg": case_icg,
            "entity_icg": entity_icg,
            "geopolitical_confidence_components": bundle.get("geopolitical_confidence_components")
            or bundle.get("components")
            or [],
            "entity_confidence_components": bundle.get("entity_confidence_components") or [],
            "geopolitical_confidence_formula": bundle.get("geopolitical_confidence_formula"),
            "entity_confidence_formula": bundle.get("entity_confidence_formula"),
            "entity_confidence_detail": bundle.get("entity_confidence_detail"),
            "confidence_detail": bundle.get("confidence_detail"),
            "gpr_case_level": bundle.get("gpr_case_level"),
            "gpr_multiplier_applied": bundle.get("gpr_multiplier_applied"),
            "eina_gma": bundle.get("eina_gma"),
            "eina_gma_formula": bundle.get("eina_gma_formula"),
            "eina_gma_components": bundle.get("eina_gma_components"),
            "sanction_impact_score": bundle.get("sanction_impact_score"),
            "sanction_drivers": bundle.get("sanction_drivers") or [],
            "sanction_entity_impacts": bundle.get("sanction_entity_impacts") or [],
            "sanction_scenario_adjustments": bundle.get("sanction_scenario_adjustments") or {},
            "sanction_trend_signals": bundle.get("sanction_trend_signals") or [],
            "driver_interactions": bundle.get("driver_interactions") or [],
            "eina_confidence_pct": headline_icg,
            "eina_confidence_source": bundle.get("confidence_source"),
            "eina_confidence_detail": bundle.get("entity_confidence_detail")
            or bundle.get("confidence_detail"),
            "osint_signals": (bundle.get("actor_impact_snapshot") or {}).get("osint_signals"),
        }
