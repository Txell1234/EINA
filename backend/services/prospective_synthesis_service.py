"""Deterministic synthesis from Godet + geo + financial artifacts for an inquiry."""
from __future__ import annotations

from typing import Any


class ProspectiveSynthesisService:
    """Aggregate pre-computed data only — no LLM conclusions."""

    def synthesize(
        self,
        *,
        question: str,
        parsed_trigger: dict[str, Any],
        actor_impact: dict[str, Any] | None = None,
        scenarios: list[dict[str, Any]] | None = None,
        financial_crossover: dict[str, Any] | None = None,
        policy_industry: dict[str, Any] | None = None,
        morph_bootstrap: dict[str, Any] | None = None,
        scope_audit: dict[str, Any] | None = None,
        godet_ready: bool = False,
    ) -> dict[str, Any]:
        reasoning: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        scenario_rows = scenarios or []
        if not scenario_rows and actor_impact:
            scenario_rows = actor_impact.get("scenarios") or []

        scenario_probs: list[float] = []
        for sc in scenario_rows:
            pct = sc.get("estimated_probability_pct") or sc.get("probability")
            if isinstance(pct, (int, float)):
                scenario_probs.append(float(pct))
            elif isinstance(pct, str) and pct.replace(".", "", 1).isdigit():
                scenario_probs.append(float(pct))

        avg_scenario = round(sum(scenario_probs) / len(scenario_probs), 1) if scenario_probs else None

        ai = actor_impact or {}
        signals = ai.get("osint_signals") or {}
        hostile = signals.get("hostile_statements", 0)
        cooperative = signals.get("cooperative_statements", 0)

        probability_pct: float | None = None
        possibility = "PLAUSIBLE"
        possibility_rationale = "Sense dades Godet completes; possibilitat per defecte."

        if scenario_probs:
            probability_pct = avg_scenario
            reasoning.append(
                {
                    "conclusion": f"Probabilitat mitjana escenaris Godet: {avg_scenario}%",
                    "because": (
                        f"Mitjana de {len(scenario_probs)} escenaris amb probabilitats ajustades per OSINT: "
                        f"{', '.join(str(p) for p in scenario_probs)}."
                    ),
                    "sources": [{"origin": "eina_prospective", "field": "scenarios.probability"}],
                }
            )

        if scenario_rows:
            for sc in scenario_rows[:4]:
                poss = sc.get("possibility") or "PLAUSIBLE"
                if sc.get("scenario_type") in ("infern", "tensio") and hostile >= 3:
                    possibility = poss
                    possibility_rationale = sc.get("possibility_rationale") or (
                        f"Escenari {sc.get('name')}: {hostile} declaracions hostils al corpus OSINT."
                    )
                evidence.append(
                    {
                        "kind": "scenario",
                        "label": sc.get("name", ""),
                        "value": sc.get("estimated_probability_pct"),
                        "possibility": poss,
                        "origin": "eina_prospective",
                    }
                )

        if hostile or cooperative:
            reasoning.append(
                {
                    "conclusion": f"Senyals OSINT: {hostile} hostils, {cooperative} cooperatives",
                    "because": "Comptatge directe de declaracions extretes amb postura ≤−1 o ≥+1.",
                    "sources": [{"origin": "osint_extraction", "field": "posture_value"}],
                }
            )

        fc = financial_crossover or {}
        crossover = fc.get("crossover") or {}
        final_nums = crossover.get("final_numbers") or {}
        fin_mode = fc.get("mode", "full" if crossover else "none")
        if final_nums.get("blended_return_index") is not None:
            reasoning.append(
                {
                    "conclusion": f"Índex retorn combinat ({fin_mode}): {final_nums['blended_return_index']}",
                    "because": (
                        crossover.get("final_numbers_explanations", {})
                        .get("blended_return_index", {})
                        .get("because", "Crossover financer determinista.")
                    ),
                    "sources": [{"origin": "financial_crossover", "field": "blended_return_index"}],
                }
            )
        for align in crossover.get("alignments") or []:
            if align.get("because"):
                reasoning.append(
                    {
                        "conclusion": align.get("summary", "Alineació financer-policy"),
                        "because": align["because"],
                        "sources": align.get("sources") or [{"origin": "financial_crossover"}],
                    }
                )

        policy = policy_industry or fc.get("policy_industry") or {}
        companies = policy.get("companies") or []
        if companies:
            names = ", ".join(c.get("name", "") for c in companies[:4])
            reasoning.append(
                {
                    "conclusion": f"Policy×Indústria: {len(companies)} empreses vinculades",
                    "because": f"Mapatge per premisa de la pregunta: {names}.",
                    "sources": [{"origin": "eina_policy_industry", "field": "companies"}],
                }
            )
            evidence.append(
                {
                    "kind": "policy_industry",
                    "label": "Empreses mapejades",
                    "value": len(companies),
                    "origin": "eina_policy_industry",
                }
            )

        morph = morph_bootstrap or {}
        if morph.get("godet_preview"):
            preview = morph["godet_preview"]
            reasoning.append(
                {
                    "conclusion": f"Previsualització morfològica: {len(preview)} escenaris candidats",
                    "because": (
                        f"Espai combinatòri valid: {morph.get('valid_combinations_count', 0)} combinacions "
                        f"després de CCA ({morph.get('methodology', 'rule_based')})."
                    ),
                    "sources": [{"origin": "morph_bootstrap", "field": "godet_preview"}],
                }
            )
            for row in preview[:2]:
                evidence.append(
                    {
                        "kind": "morph_preview",
                        "label": row.get("name", ""),
                        "value": row.get("possibility"),
                        "origin": "morph_bootstrap",
                    }
                )

        if scope_audit:
            removed = scope_audit.get("removed_topic", 0) + scope_audit.get("removed_must_match", 0)
            if removed:
                reasoning.append(
                    {
                        "conclusion": f"Filtre inquiry: {removed} articles descartats per fora de tema",
                        "because": "Articles sense termes obligatoris de la pregunta o per sota del llindar.",
                        "sources": [{"origin": "inquiry_scope", "field": "scope_audit"}],
                    }
                )

        conclusions: list[str] = []
        if probability_pct is not None:
            conclusions.append(
                f"Probabilitat estimada (escenaris Godet): {probability_pct}% — "
                f"basada en dades OSINT i ajustos traçables, no en inferència LLM."
            )
        else:
            conclusions.append(
                "Completa l'anàlisi prospectiu (MIC-MAC, MACTOR, morfològic, SMIC) "
                "i torna a executar la síntesi per obtenir probabilitats."
            )

        if not godet_ready:
            conclusions.append(
                "Estat: Godet pendent — MIC-MAC i MACTOR es mantenen manuals al wizard d'Anàlisi Prospectiva."
            )

        return {
            "question": question,
            "probability_pct": probability_pct,
            "possibility": possibility,
            "possibility_rationale": possibility_rationale,
            "confidence": min(95, 40 + len(evidence) * 8 + (10 if godet_ready else 0)),
            "reasoning": reasoning,
            "evidence": evidence,
            "conclusions": conclusions,
            "methodology": "deterministic_synthesis",
            "llm_used_in_conclusions": False,
            "godet_ready": godet_ready,
            "parsed_trigger_summary": {
                "actors": parsed_trigger.get("actors", []),
                "horizon": parsed_trigger.get("horizon_label", ""),
                "required_terms": parsed_trigger.get("required_terms", []),
            },
            "financial_mode": fin_mode,
            "policy_companies_count": len(companies),
            "morph_valid_combinations": morph.get("valid_combinations_count"),
        }
