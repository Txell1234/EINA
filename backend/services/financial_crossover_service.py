"""Cross-reference external financial reports with EINA case conclusions and probabilities."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.external_report import CaseExternalReport
from models.investments import InvestmentRecommendation
from models.prospective import ProspectiveProject, ProspectiveScenario
from services.financial_document_service import (
    is_valid_company_name,
    parse_financial_document,
    sanitize_parsed_metrics,
)
from services.policy_industry_service import PolicyIndustryService

logger = logging.getLogger(__name__)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _blend(a: float | None, b: float | None, weight_external: float = 0.35) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    w = max(0.0, min(1.0, weight_external))
    return round(a * (1 - w) + b * w, 2)


def _source(
    origin: str,
    field: str,
    value: Any,
    *,
    label: str = "",
    excerpt: str = "",
) -> dict[str, Any]:
    return {
        "origin": origin,
        "field": field,
        "value": value,
        "label": label or field,
        "excerpt": excerpt[:200] if excerpt else "",
    }


def _metrics_without_llm(metrics: dict[str, Any]) -> dict[str, Any]:
    """Crossover uses only rule-parsed fields — never LLM-invented metrics."""
    clean = {k: v for k, v in metrics.items() if k != "llm_extracted"}
    return clean


def _smic_probability_values(smic: dict[str, Any] | None) -> list[float]:
    """SMIC initial_probs may be a list (Godet) or legacy dict."""
    if not smic:
        return []
    raw = smic.get("initial_probs")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [float(v) for v in raw if isinstance(v, (int, float))]
    if isinstance(raw, dict):
        return [float(v) for v in raw.values() if isinstance(v, (int, float))]
    return []


class FinancialCrossoverService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_project(
        self, case_id: int, project_id: int | None = None
    ) -> ProspectiveProject | None:
        if project_id:
            r = await self.db.execute(
                select(ProspectiveProject).where(
                    ProspectiveProject.id == project_id,
                    ProspectiveProject.case_id == case_id,
                )
            )
            project = r.scalar_one_or_none()
            if project:
                return project
        r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    async def _eina_metrics(
        self,
        case_id: int,
        *,
        project_id: int | None = None,
        focus_company: str | None = None,
    ) -> dict[str, Any]:
        from services.prospective_service import ProspectiveService

        project = await self._resolve_project(case_id, project_id)
        out: dict[str, Any] = {
            "project_id": project.id if project else None,
            "scenarios": [],
            "smic": None,
            "investment_recommendations": [],
            "policy_companies": [],
        }

        if project:
            svc = ProspectiveService(self.db)
            smic = await svc.get_smic(project.id)
            out["smic"] = smic

            sc_r = await self.db.execute(
                select(ProspectiveScenario).where(ProspectiveScenario.project_id == project.id)
            )
            for sc in sc_r.scalars().all():
                out["scenarios"].append(
                    {
                        "id": sc.id,
                        "name": sc.name,
                        "type": sc.scenario_type,
                        "probability": sc.probability,
                        "possibility": getattr(sc, "possibility", None),
                    }
                )

        rec_r = await self.db.execute(
            select(InvestmentRecommendation)
            .where(InvestmentRecommendation.case_id == case_id)
            .order_by(InvestmentRecommendation.created_at.desc())
            .limit(10)
        )
        for rec in rec_r.scalars().all():
            rtype = rec.recommendation_type
            out["investment_recommendations"].append(
                {
                    "id": rec.id,
                    "type": rtype.value if hasattr(rtype, "value") else str(rtype),
                    "confidence_pct": rec.confidence_percentage,
                    "rationale": (rec.rationale or "")[:300],
                }
            )

        policy = await PolicyIndustryService(self.db).build_map(case_id)
        policy_rows = policy.get("companies") or []
        out["policy_companies"] = [
            {
                "name": c["name"],
                "region": c.get("region"),
                "why": c.get("beneficiary_rationale", "")[:200],
            }
            for c in policy_rows[:12]
        ]
        if focus_company:
            from services.actor_impact_utils import canonical_actor

            focus_key = canonical_actor(focus_company).lower()
            matched = [
                c
                for c in policy_rows
                if canonical_actor(c.get("name", "")).lower() == focus_key
                or focus_key in (c.get("name") or "").lower()
            ]
            out["focus_company"] = focus_company
            out["entity_focus_match"] = (
                {
                    "name": matched[0]["name"],
                    "region": matched[0].get("region"),
                    "why": matched[0].get("beneficiary_rationale", "")[:200],
                }
                if matched
                else None
            )

        return out

    async def _compute_eina_confidence(
        self,
        case_id: int,
        eina: dict[str, Any],
        *,
        focus_company: str | None = None,
        external_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Índex de Confiança Geopolítica (ICG) derivat del cas — separat de la postura
        d'inversió (HOLD 50% per defecte no contamina l'ICG).
        """
        from services.actor_impact_service import ActorImpactService
        from services.geopolitical_confidence import build_geopolitical_confidence_bundle

        impact: dict[str, Any] = {}
        try:
            svc = ActorImpactService(self.db)
            impact = await svc.get_latest(case_id) or {}
            if not impact.get("has_data"):
                impact = await svc.build_assessment(case_id, project_id=eina.get("project_id"))
        except Exception as exc:
            logger.debug("actor_impact confidence skip: %s", exc)

        effective_focus = focus_company or eina.get("focus_company")
        registry_row: dict[str, Any] | None = None
        external_metrics: dict[str, Any] | None = None
        if effective_focus:
            from services.company_registry_service import load_company_registry
            from services.geo_intelligence_service import (
                _external_metrics_for_entity,
                _registry_row_for_company,
            )

            registry = await load_company_registry(
                self.db, case_id, project_id=eina.get("project_id")
            )
            registry_row = _registry_row_for_company(registry, effective_focus)
            if external_metrics is None:
                external_metrics = await _external_metrics_for_entity(
                    self.db, case_id, effective_focus
                )

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
        posture = bundle.get("investment_posture") or {}
        if posture.get("source") == "default_fallback":
            bundle["investment_posture_detail"] = (
                "Recomanació HOLD 50% per defecte — no reflecteix OSINT del cas. "
                "Executa intel·ligència o POST /api/investments/analyze/{case_id}."
            )
        from services.geo_intelligence_service import derive_driver_interactions

        bundle["driver_interactions"] = derive_driver_interactions(bundle)
        return bundle

    @staticmethod
    def _policy_company_matches(
        metrics: dict[str, Any],
        policy_companies: list[dict[str, Any]],
        *,
        focus_company: str | None = None,
    ) -> list[dict[str, Any]]:
        """Match policy companies by focus, parsed company name, or ticker — not random substrings."""
        from services.actor_impact_utils import canonical_actor

        if not policy_companies:
            return []

        names_to_try: list[str] = []
        if focus_company:
            names_to_try.append(focus_company)
        if metrics.get("company_name"):
            names_to_try.append(str(metrics["company_name"]))

        matched: list[dict[str, Any]] = []
        seen: set[str] = set()
        for needle in names_to_try:
            key = canonical_actor(needle).lower()
            if not key:
                continue
            for co in policy_companies:
                co_key = canonical_actor(co.get("name", "")).lower()
                if not co_key or co_key in seen:
                    continue
                if co_key == key or key in co_key or co_key in key:
                    matched.append(co)
                    seen.add(co_key)

        tickers = [t for t in (metrics.get("tickers_mentioned") or []) if len(t) >= 3]
        for ticker in tickers:
            for co in policy_companies:
                co_key = canonical_actor(co.get("name", "")).lower()
                if co_key in seen:
                    continue
                if ticker.lower() in co.get("name", "").lower().replace(" ", ""):
                    matched.append(co)
                    seen.add(co_key)

        return matched[:5]

    async def _resolve_report_context(
        self,
        case_id: int,
        metrics: dict[str, Any],
        *,
        focus_company: str | None = None,
        title: str = "",
        project_id: int | None = None,
    ) -> dict[str, Any]:
        """Link uploaded report to EINA company registry (Godet / Policy×Indústria)."""
        from services.actor_impact_utils import canonical_actor
        from services.company_registry_service import load_company_registry

        registry = await load_company_registry(self.db, case_id, project_id=project_id)
        reg_companies = registry.get("companies") or []

        def _match_registry(name: str) -> dict[str, Any] | None:
            key = canonical_actor(name).lower()
            if not key:
                return None
            for row in reg_companies:
                row_key = canonical_actor(row.get("name", "")).lower()
                if not row_key:
                    continue
                if row_key == key or key in row_key or row_key in key:
                    return row
            return None

        detected = list(metrics.get("detected_companies") or [])
        cn = metrics.get("company_name")
        if cn and is_valid_company_name(cn) and not any(d.get("name") == cn for d in detected):
            detected.insert(
                0,
                {
                    "name": cn,
                    "match_kind": "report_header",
                    "score": 50,
                },
            )

        candidates: list[tuple[str, str, dict[str, Any] | None]] = []
        user_ref = metrics.get("reference_entity")
        if user_ref:
            candidates.append((str(user_ref), "user_reference", _match_registry(str(user_ref))))
        if focus_company:
            candidates.append((focus_company, "user_focus", _match_registry(focus_company)))
        for d in detected:
            candidates.append((d["name"], d.get("match_kind", "detected"), _match_registry(d["name"])))
        if title:
            from services.financial_document_service import detect_companies_in_text

            for d in detect_companies_in_text("", title=title):
                candidates.append((d["name"], "report_title", _match_registry(d["name"])))

        resolved_row: dict[str, Any] | None = None
        resolved_name: str | None = None
        resolved_source: str | None = None
        for name, src, row in candidates:
            if row:
                resolved_row = row
                resolved_name = row.get("name") or name
                resolved_source = src
                break
        if not resolved_row and candidates:
            resolved_name = candidates[0][0]
            resolved_source = candidates[0][1]

        eina_link: dict[str, Any] = {"found": False}
        if resolved_row:
            eina_link = {
                "found": True,
                "name": resolved_row.get("name"),
                "country": resolved_row.get("country"),
                "region": resolved_row.get("region"),
                "roles": resolved_row.get("roles") or [],
                "sectors": resolved_row.get("sectors") or [],
                "origins": resolved_row.get("origins") or [],
                "beneficiary_rationale": resolved_row.get("beneficiary_rationale") or "",
                "policy_link": resolved_row.get("policy_link") or "",
                "linked_aspects": resolved_row.get("linked_aspects") or [],
                "contractor_relationships": resolved_row.get("contractor_relationships") or [],
                "ticker": resolved_row.get("ticker") or "",
            }
        elif resolved_name:
            for d in detected:
                if d.get("name") == resolved_name and d.get("beneficiary_rationale"):
                    eina_link = {
                        "found": True,
                        "name": resolved_name,
                        "beneficiary_rationale": d.get("beneficiary_rationale", ""),
                        "policy_link": d.get("policy_link", ""),
                        "origins": ["reference_profile"],
                        "note": "Perfil de referència; encara no al registre viu del cas.",
                    }
                    break

        from services.financial_document_service import build_report_narrative
        from services.investwatch_report_view import build_investwatch_report_view

        narrative_company = (
            metrics.get("reference_entity")
            or resolved_name
            or (metrics.get("company_name") if cn and is_valid_company_name(cn) else None)
        )
        rule_narrative = build_report_narrative(
            narrative_company,
            title=title,
            eina_link=eina_link,
            metrics=metrics,
        )
        investwatch_report = build_investwatch_report_view(
            metrics,
            report_context={
                "resolved_company": resolved_name,
                "eina_link": eina_link,
                "narrative": rule_narrative,
                "title": title,
            },
            title=title,
        )
        investwatch_report["narrative"] = rule_narrative
        return {
            "report_about": (
                metrics.get("reference_entity")
                or resolved_name
                or (cn if cn and is_valid_company_name(cn) else None)
            ),
            "title": title,
            "resolved_company": resolved_name,
            "reference_entity": metrics.get("reference_entity"),
            "reference_entity_source": metrics.get("reference_entity_source"),
            "resolution_source": resolved_source,
            "detected_companies": detected[:6],
            "eina_link": eina_link,
            "narrative": rule_narrative,
            "narrative_source": "rules",
            "narrative_rule": rule_narrative,
            "investwatch_report": investwatch_report,
            "llm_narrative": None,
            "needs_llm_narrative": False,
            "llm_narrative_reason": "rules_sufficient",
        }

    async def _enrich_report_context_narrative(
        self,
        context: dict[str, Any],
        metrics: dict[str, Any],
        *,
        raw_text: str,
        title: str,
        interpret_narrative: str = "auto",
    ) -> dict[str, Any]:
        """Optionally replace rule narrative with LLM prose when rules are insufficient."""
        from services.financial_document_service import (
            interpret_report_narrative_llm,
            needs_llm_narrative,
        )

        rule_narrative = context.get("narrative_rule") or context.get("narrative") or ""
        need_llm, llm_reason = needs_llm_narrative(raw_text, metrics, title=title)
        context["needs_llm_narrative"] = need_llm
        context["llm_narrative_reason"] = llm_reason

        use_llm = interpret_narrative == "on" or (interpret_narrative != "off" and need_llm)
        if not use_llm or not raw_text.strip():
            context["narrative_source"] = "rules"
            return context

        structured_summary = {
            "company": context.get("resolved_company") or metrics.get("company_name"),
            "primary_recommendation": metrics.get("primary_recommendation"),
            "parse_mode": metrics.get("parse_mode"),
            "investwatch_summary": metrics.get("investwatch_summary"),
            "key_metrics": (metrics.get("key_metrics") or [])[:4],
        }
        llm_block = await interpret_report_narrative_llm(
            raw_text,
            company=context.get("resolved_company") or metrics.get("company_name"),
            eina_context={"title": title, "eina_link": context.get("eina_link") or {}},
            structured_summary=structured_summary,
        )
        if llm_block:
            context["narrative"] = llm_block["narrative"]
            context["narrative_source"] = "llm"
            context["llm_narrative"] = llm_block
        else:
            context["narrative_source"] = "rules"
            context["llm_narrative"] = {
                "llm_used": False,
                "fallback": "Provider no disponible o error — s'usa narrativa per regles.",
            }
        return context

    @staticmethod
    def _report_context_narrative(
        company: str | None,
        eina_link: dict[str, Any],
        title: str,
    ) -> str:
        if not company:
            return (
                "No s'ha identificat l'empresa de l'informe. "
                "Enganxa el resum PRAAMS amb el nom de l'empresa o selecciona-la al registre EINA abans de creuar."
            )
        parts = [f"Aquest informe es refereix a {company}."]
        if title:
            parts.append(f"Títol: {title[:120]}.")
        if eina_link.get("found"):
            parts.append(
                f"EINA la té al mapa del cas ({', '.join(eina_link.get('origins') or ['policy'])}) "
                f"com a actor vinculat a la política analitzada."
            )
            if eina_link.get("beneficiary_rationale"):
                parts.append(eina_link["beneficiary_rationale"][:220])
        else:
            parts.append(
                "Encara no apareix al registre d'empreses del cas — completa Godet/OSINT o selecciona-la manualment."
            )
        return " ".join(parts)

    def _build_suggested_actions(
        self,
        metrics: dict[str, Any],
        eina: dict[str, Any],
        *,
        focus_company: str | None = None,
        policy_companies: list[dict[str, Any]] | None = None,
        report_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Rule-based investment actions from structured parse + EINA context."""
        actions: list[dict[str, Any]] = []
        ext_rec = metrics.get("primary_recommendation") or metrics.get("derived_signal")
        iw = metrics.get("investwatch_summary") or {}
        inv_recs = eina.get("investment_recommendations") or []
        eina_type = (inv_recs[0].get("type") or "").upper() if inv_recs else None
        parse_mode = metrics.get("parse_mode") or "unknown"
        parse_quality = metrics.get("parse_quality") or "partial"
        report_co = (
            (report_context or {}).get("resolved_company")
            or metrics.get("reference_entity")
            or (
                metrics.get("company_name")
                if is_valid_company_name(metrics.get("company_name"))
                else None
            )
        )
        eina_link = (report_context or {}).get("eina_link") or {}

        if report_co and eina_link.get("found"):
            actions.append(
                {
                    "action": "CONTEXT_OK",
                    "horizon": "Informe vinculat",
                    "company": report_co,
                    "because": (
                        f"Informe identificat com a {report_co}. "
                        f"{(eina_link.get('beneficiary_rationale') or '')[:200]}"
                    ).strip(),
                    "source": "eina_report_link",
                }
            )

        if ext_rec:
            src_label = "informe_extern"
            because_extra = (
                " (inferit del text: creixement, upside o moviment bursàtil)"
                if metrics.get("derived_signal") and not metrics.get("primary_recommendation")
                else f" ({parse_mode})"
            )
            actions.append(
                {
                    "action": ext_rec,
                    "horizon": "6-12 mesos",
                    "because": (
                        f"Senyal extern {ext_rec}{because_extra}. "
                        + (
                            "Línia Recommendation/Rating explícita."
                            if metrics.get("primary_recommendation")
                            else "Derivat de mètriques de creixement / upside / notícia."
                        )
                    ),
                    "source": src_label,
                }
            )
        elif iw.get("avg_return_score") is not None and iw.get("avg_risk_score") is not None:
            signal = iw.get("signal")
            if signal == "more_return_than_risk":
                actions.append(
                    {
                        "action": "BUY",
                        "horizon": "6-12 mesos",
                        "because": (
                            f"InvestWatch: retorn mitjà {iw['avg_return_score']}/7 > "
                            f"risc {iw['avg_risk_score']}/7."
                        ),
                        "source": "informe_extern",
                    }
                )
            elif signal == "more_risk_than_return":
                actions.append(
                    {
                        "action": "REDUCE_OR_HOLD",
                        "horizon": "3-6 mesos",
                        "because": (
                            f"InvestWatch: risc {iw['avg_risk_score']}/7 ≥ "
                            f"retorn {iw['avg_return_score']}/7."
                        ),
                        "source": "informe_extern",
                    }
                )

        growth_metrics = [m for m in (metrics.get("key_metrics") or []) if m.get("metric_kind") == "growth"]
        if growth_metrics and not ext_rec and not iw.get("avg_return_score"):
            highlights = ", ".join(f"{m['label']} {m['value_pct']}%" for m in growth_metrics[:4])
            trend = sum(m["value_pct"] for m in growth_metrics[:4]) / min(4, len(growth_metrics))
            action = "MONITOR" if trend < 5 else "REVIEW_POSITIVE"
            actions.append(
                {
                    "action": action,
                    "horizon": "Trimestre",
                    "because": f"Mètriques de creixement extretes: {highlights}.",
                    "source": "informe_extern",
                }
            )

        scenarios = eina.get("scenarios") or []
        if parse_quality in ("weak", "partial") and scenarios and report_co:
            top = max(
                scenarios,
                key=lambda s: float(s.get("probability") or 0)
                if str(s.get("probability", "")).replace(".", "", 1).isdigit()
                else 0,
            )
            prob = top.get("probability")
            actions.append(
                {
                    "action": "ALIGN_WITH_SCENARIO",
                    "horizon": "12-24 mesos",
                    "company": report_co,
                    "because": (
                        f"Parser extern limitat; escenari Godet dominant «{top.get('name', '?')}» "
                        f"(probabilitat {prob}%) contextualitza la decisió per {report_co}."
                    ),
                    "source": "eina_scenarios",
                }
            )

        if eina_type and ext_rec:
            if ext_rec in eina_type or eina_type in ext_rec:
                actions.append(
                    {
                        "action": ext_rec,
                        "horizon": "6-12 mesos",
                        "because": (
                            f"Convergència: informe {ext_rec} alineat amb recomanació EINA {eina_type} "
                            f"(confiança {inv_recs[0].get('confidence_pct')}%)."
                        ),
                        "source": "eina_synthesis",
                    }
                )
            else:
                actions.append(
                    {
                        "action": "REVIEW",
                        "horizon": "Abans d'operar",
                        "because": (
                            f"Divergència: informe {ext_rec} vs EINA {eina_type}. "
                            "Contrastar amb escenaris Godet i mapa Policy×Indústria abans d'invertir."
                        ),
                        "source": "eina_synthesis",
                    }
                )
        elif eina_type and not ext_rec and parse_quality == "weak":
            actions.append(
                {
                    "action": eina_type,
                    "horizon": "Referència interna EINA",
                    "because": (
                        f"Parser extern insuficient per {report_co or 'l\'entitat'}; "
                        f"posició interna del cas: {eina_type} (confiança {inv_recs[0].get('confidence_pct')}%). "
                        "Complementa amb PRAAMS 1-7 o selecciona l'empresa al desplegable."
                    ),
                    "source": "eina_internal_fallback",
                }
            )
        elif eina_type and not ext_rec and parse_quality != "weak":
            pass

        policy = policy_companies or []
        if focus_company:
            for co in self._policy_company_matches(metrics, policy, focus_company=focus_company):
                if co.get("why"):
                    actions.append(
                        {
                            "action": "MONITOR_POLICY",
                            "horizon": "Continu",
                            "company": co.get("name"),
                            "because": co["why"][:280],
                            "source": "eina_policy_industry",
                        }
                    )
                    break

        if not actions and metrics.get("parse_warning"):
            actions.append(
                {
                    "action": "RE-PASTE",
                    "horizon": "—",
                    "because": metrics["parse_warning"],
                    "source": "parser",
                }
            )

        llm_narr = (report_context or {}).get("llm_narrative") or {}
        action_hint = (llm_narr.get("action_hint") or "").strip()
        if (
            action_hint
            and llm_narr.get("llm_used")
            and not ext_rec
            and not iw.get("avg_return_score")
            and len(actions) <= 1
        ):
            actions.append(
                {
                    "action": action_hint.upper()[:32],
                    "horizon": "Segons interpretació IA",
                    "company": report_co,
                    "because": (
                        "Senyal qualitatiu extret per IA del cos de l'informe "
                        "(només quan el parser estructurat no n'ha trobat prou)."
                    ),
                    "source": "llm_narrative",
                }
            )

        return actions[:6]

    @staticmethod
    def _enrich_suggested_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from services.crossover_recommendation_service import _enrich_recommendation

        return [_enrich_recommendation(a) for a in actions]

    def _collect_external_evidence(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        display_co = (
            metrics.get("reference_entity")
            or (
                metrics.get("company_name")
                if is_valid_company_name(metrics.get("company_name"))
                else None
            )
        )
        if display_co:
            evidence.append(
                {
                    "kind": "company",
                    "label": "Empresa informe",
                    "value": display_co,
                    "origin": "informe_extern",
                    "because": "Nom vinculat per referència EINA, parser o títol (no fragments de text).",
                }
            )
        if metrics.get("derived_signal") and not metrics.get("primary_recommendation"):
            evidence.append(
                {
                    "kind": "derived_signal",
                    "label": "Senyal inferit",
                    "value": metrics["derived_signal"],
                    "origin": "informe_extern",
                    "because": "Inferit de creixement, upside o moviment bursàtil al text.",
                }
            )
        if metrics.get("parse_quality"):
            evidence.append(
                {
                    "kind": "parse_quality",
                    "label": "Qualitat parseig",
                    "value": metrics["parse_quality"],
                    "origin": "informe_extern",
                    "because": "good=estructurat; partial=notícia filtrada; weak=cal referència manual.",
                }
            )
        if metrics.get("parse_mode"):
            evidence.append(
                {
                    "kind": "parse_mode",
                    "label": "Mode parseig",
                    "value": metrics["parse_mode"],
                    "origin": "informe_extern",
                    "because": "investwatch = puntuacions 1-7; financial_news = mètriques clau filtrades.",
                }
            )
        for factor in metrics.get("return_factors") or []:
            evidence.append(
                {
                    "kind": "return_factor",
                    "label": factor.get("label", ""),
                    "value": f"{factor.get('score')}/7",
                    "origin": "informe_extern",
                    "because": f"Factor retorn InvestWatch ({factor.get('score')}/7).",
                }
            )
        for factor in metrics.get("risk_factors") or []:
            evidence.append(
                {
                    "kind": "risk_factor",
                    "label": factor.get("label", ""),
                    "value": f"{factor.get('score')}/7",
                    "origin": "informe_extern",
                    "because": f"Factor risc InvestWatch ({factor.get('score')}/7).",
                }
            )
        for km in metrics.get("key_metrics") or []:
            evidence.append(
                {
                    "kind": "key_metric",
                    "label": km.get("label", ""),
                    "value": f"{km.get('value_pct')}%",
                    "origin": "informe_extern",
                    "because": km.get("snippet") or "Mètrica financera amb etiqueta reconeguda (revenue, profit, etc.).",
                }
            )
        for prob in metrics.get("probabilities") or []:
            evidence.append(
                {
                    "kind": "probability",
                    "label": prob.get("label", ""),
                    "value": f"{prob.get('value_pct')}%",
                    "origin": "informe_extern",
                    "because": "Probabilitat amb etiqueta explícita al text.",
                }
            )
        ext_rec = metrics.get("primary_recommendation")
        if ext_rec:
            evidence.append(
                {
                    "kind": "recommendation",
                    "label": "Recomanació principal",
                    "value": ext_rec,
                    "origin": "informe_extern",
                    "because": "Línia Recommendation/Rating/InvestWatch — no paraules BUY/SELL disperses.",
                }
            )
        iw = metrics.get("investwatch_summary") or {}
        if iw:
            evidence.append(
                {
                    "kind": "investwatch_summary",
                    "label": "Resum InvestWatch",
                    "value": (
                        f"retorn mitjà {iw.get('avg_return_score')}/7, "
                        f"risc mitjà {iw.get('avg_risk_score')}/7, senyal {iw.get('signal')}"
                    ),
                    "origin": "informe_extern",
                    "because": "Mitjana de puntuacions 1-7 (factors retorn/risc).",
                }
            )
        return evidence

    def _collect_eina_evidence(self, eina: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for sc in eina.get("scenarios") or []:
            evidence.append(
                {
                    "kind": "scenario",
                    "label": sc.get("name") or f"Escenari #{sc.get('id')}",
                    "value": sc.get("probability"),
                    "origin": "eina_prospective",
                    "because": "Probabilitat registrada a l'escenari Godet del projecte prospectiu del cas.",
                }
            )
        for rec in eina.get("investment_recommendations") or []:
            evidence.append(
                {
                    "kind": "investment",
                    "label": f"Recomanació {rec.get('type')}",
                    "value": f"{rec.get('confidence_pct')}% confiança",
                    "origin": "eina_investments",
                    "because": (rec.get("rationale") or "Confiança emmagatzemada a la recomanació d'inversió del cas.")[:200],
                }
            )
        smic = eina.get("smic") or {}
        for i, val in enumerate(_smic_probability_values(smic)):
            evidence.append(
                {
                    "kind": "smic",
                    "label": f"SMIC prob. inicial #{i + 1}",
                    "value": val,
                    "origin": "eina_smic",
                    "because": "Probabilitat inicial SMIC del projecte prospectiu.",
                }
            )
        for co in eina.get("policy_companies") or []:
            evidence.append(
                {
                    "kind": "policy_company",
                    "label": co.get("name", ""),
                    "value": co.get("region", ""),
                    "origin": "eina_policy_industry",
                    "because": co.get("why") or "Empresa del mapa Policy×Indústria del cas.",
                }
            )
        return evidence

    def _external_implied_risk(self, metrics: dict[str, Any]) -> tuple[float | None, list[dict[str, Any]]]:
        iw = metrics.get("investwatch_summary") or {}
        if iw.get("avg_risk_score") is not None:
            avg = float(iw["avg_risk_score"])
            index = round(avg / 7 * 100, 1)
            factors = metrics.get("risk_factors") or []
            labels = ", ".join(f"{f['label']} {f['score']}/7" for f in factors[:6])
            return index, [
                _source(
                    "informe_extern",
                    "investwatch_summary.avg_risk_score",
                    avg,
                    label="Mitjana risc 1-7",
                ),
                _source(
                    "informe_extern",
                    "risk_factors",
                    labels or "—",
                    label="Factors de risc extrets",
                ),
            ]
        return None, []

    def _external_implied_return(self, metrics: dict[str, Any]) -> tuple[float | None, list[dict[str, Any]]]:
        iw = metrics.get("investwatch_summary") or {}
        if iw.get("avg_return_score") is not None:
            avg = float(iw["avg_return_score"])
            index = round(avg / 7 * 100, 1)
            factors = metrics.get("return_factors") or []
            labels = ", ".join(f"{f['label']} {f['score']}/7" for f in factors[:6])
            return index, [
                _source(
                    "informe_extern",
                    "investwatch_summary.avg_return_score",
                    avg,
                    label="Mitjana retorn 1-7",
                ),
                _source(
                    "informe_extern",
                    "return_factors",
                    labels or "—",
                    label="Factors de retorn extrets",
                ),
            ]
        pcts = metrics.get("key_metrics") or metrics.get("percentages") or []
        growth_pcts = [
            p
            for p in pcts
            if p.get("metric_kind") == "growth"
            or (
                any(
                    k in (p.get("label") or "").lower()
                    for k in ("revenue", "eps", "earnings", "profit", "sales", "growth", "upside")
                )
                and p.get("metric_kind") != "ratio"
            )
        ]
        upside = metrics.get("fair_value_upside_pct")
        if isinstance(upside, (int, float)):
            return float(upside), [
                _source(
                    "informe_extern",
                    "fair_value_upside_pct",
                    upside,
                    label="Upside valor just",
                )
            ]
        if growth_pcts:
            val = round(sum(p["value_pct"] for p in growth_pcts[:3]) / len(growth_pcts[:3]), 1)
            labels = ", ".join(f"{p['label']} {p['value_pct']}%" for p in growth_pcts[:3])
            return val, [
                _source(
                    "informe_extern",
                    "key_metrics",
                    val,
                    label="Mitjana mètriques de creixement (no ratios ROA/RoCE)",
                    excerpt=labels,
                )
            ]
        return None, []

    def _build_crossover(
        self,
        external: dict[str, Any],
        eina: dict[str, Any],
        *,
        external_weight: float = 0.35,
        focus_company: str | None = None,
        report_context: dict[str, Any] | None = None,
        registry_companies: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raw_metrics = external.get("metrics") or external
        metrics = _metrics_without_llm(raw_metrics)
        llm_stored = "llm_extracted" in raw_metrics

        ext_risk, ext_risk_sources = self._external_implied_risk(metrics)
        ext_return, ext_return_sources = self._external_implied_return(metrics)

        inv_recs = eina.get("investment_recommendations") or []
        inv_confs = [float(r["confidence_pct"]) for r in inv_recs if r.get("confidence_pct") is not None]
        computed_conf = eina.get("computed_confidence") or {}
        icg_case = computed_conf.get("case_geopolitical_confidence_index")
        if icg_case is None:
            icg_case = computed_conf.get("geopolitical_confidence_index")
        icg_entity = computed_conf.get("entity_confidence_index")
        icg = icg_entity if icg_entity is not None else icg_case
        if icg is None:
            icg = computed_conf.get("confidence_pct")
        posture = computed_conf.get("investment_posture") or {}
        if posture.get("source") == "default_fallback" and icg is None:
            eina_confidence = None
        elif icg is not None:
            eina_confidence = float(icg)
        else:
            inv_avg = _avg(inv_confs)
            rec_type = (inv_recs[0].get("type") or "HOLD").upper() if inv_recs else "HOLD"
            if inv_avg == 50.0 and rec_type == "HOLD":
                eina_confidence = None
            else:
                eina_confidence = inv_avg
        conf_sources = [
            _source(
                "eina_investments",
                f"recommendations[{i}].confidence_pct",
                r.get("confidence_pct"),
                label=f"{r.get('type')} confiança",
                excerpt=r.get("rationale") or "",
            )
            for i, r in enumerate(inv_recs[:5])
            if r.get("confidence_pct") is not None
        ]
        for c in computed_conf.get("components") or []:
            conf_sources.append(
                _source(
                    "eina_actor_impact",
                    c.get("name", "component"),
                    c.get("value"),
                    label=c.get("label") or c.get("name"),
                )
            )

        scenario_rows = eina.get("scenarios") or []
        scenario_probs: list[float] = []
        scenario_sources: list[dict[str, Any]] = []
        for i, sc in enumerate(scenario_rows):
            p = sc.get("probability")
            if isinstance(p, (int, float)):
                scenario_probs.append(float(p))
                scenario_sources.append(
                    _source(
                        "eina_prospective",
                        f"scenarios[{i}].probability",
                        p,
                        label=sc.get("name") or f"Escenari {sc.get('id')}",
                    )
                )
            elif isinstance(p, str) and p.replace(".", "", 1).isdigit():
                scenario_probs.append(float(p))
                scenario_sources.append(
                    _source(
                        "eina_prospective",
                        f"scenarios[{i}].probability",
                        float(p),
                        label=sc.get("name") or f"Escenari {sc.get('id')}",
                    )
                )
        eina_scenario_avg = _avg(scenario_probs)

        smic_values = _smic_probability_values(eina.get("smic"))

        w = max(0.0, min(1.0, external_weight))
        blended_return = _blend(ext_return, eina_confidence, w)
        eina_risk_proxy = 100 - eina_confidence if eina_confidence is not None else None
        blended_risk = _blend(ext_risk, eina_risk_proxy, w)

        external_evidence = self._collect_external_evidence(metrics)
        eina_evidence = self._collect_eina_evidence(eina)

        final_numbers = {
            "external_return_index": ext_return,
            "external_risk_index": ext_risk,
            "eina_investment_confidence_avg": eina_confidence,
            "geopolitical_confidence_index": icg,
            "case_geopolitical_confidence_index": icg_case,
            "entity_geopolitical_confidence_index": icg_entity,
            "entity_icg_delta": computed_conf.get("entity_icg_delta"),
            "eina_scenario_probability_avg": eina_scenario_avg,
            "smic_probability_sum": round(sum(smic_values), 2) if smic_values else None,
            "blended_return_index": blended_return,
            "blended_risk_index": blended_risk,
            "external_weight_used": w,
            "crossover_score_10": round(blended_return / 10, 1) if blended_return is not None else None,
        }

        number_explanations: dict[str, dict[str, Any]] = {}

        if ext_return is not None:
            iw = metrics.get("investwatch_summary") or {}
            avg = iw.get("avg_return_score")
            number_explanations["external_return_index"] = {
                "value": ext_return,
                "because": (
                    f"Mitjana retorn {avg}/7 del informe → ({avg}/7)×100 = {ext_return}."
                    if avg is not None
                    else f"Percentatge de retorn extret literalment del text: {ext_return}%."
                ),
                "formula": "(avg_return_score / 7) × 100",
                "sources": ext_return_sources,
            }

        if ext_risk is not None:
            iw = metrics.get("investwatch_summary") or {}
            avg = iw.get("avg_risk_score")
            number_explanations["external_risk_index"] = {
                "value": ext_risk,
                "because": f"Mitjana risc {avg}/7 del informe → ({avg}/7)×100 = {ext_risk}.",
                "formula": "(avg_risk_score / 7) × 100",
                "sources": ext_risk_sources,
            }

        if eina_confidence is not None:
            because = computed_conf.get("confidence_detail") or (
                f"Mitjana de {len(inv_confs)} valors de confiança de recomanacions EINA: "
                f"{' + '.join(str(c) for c in inv_confs)} → {eina_confidence}%."
                if inv_confs
                else f"Confiança calculada del cas: {eina_confidence}%."
            )
            number_explanations["eina_investment_confidence_avg"] = {
                "value": eina_confidence,
                "because": because,
                "formula": computed_conf.get("geopolitical_confidence_formula")
                or computed_conf.get("confidence_source")
                or "mean(confidence_pct)",
                "sources": conf_sources,
            }
        if computed_conf.get("geopolitical_confidence_index") is not None:
            number_explanations["geopolitical_confidence_index"] = {
                "value": icg,
                "because": computed_conf.get("entity_confidence_detail")
                or computed_conf.get("confidence_detail")
                or "",
                "formula": computed_conf.get("entity_confidence_formula")
                or computed_conf.get("geopolitical_confidence_formula")
                or "ICG weighted",
                "sources": conf_sources,
            }
        if icg_case is not None:
            number_explanations["case_geopolitical_confidence_index"] = {
                "value": icg_case,
                "because": computed_conf.get("confidence_detail") or "",
                "formula": computed_conf.get("geopolitical_confidence_formula") or "ICG_cas weighted",
                "sources": conf_sources,
            }
        if icg_entity is not None:
            number_explanations["entity_geopolitical_confidence_index"] = {
                "value": icg_entity,
                "because": computed_conf.get("entity_confidence_detail") or "",
                "formula": computed_conf.get("entity_confidence_formula") or "ICE weighted",
                "sources": conf_sources,
            }

        if eina_scenario_avg is not None:
            number_explanations["eina_scenario_probability_avg"] = {
                "value": eina_scenario_avg,
                "because": (
                    f"Mitjana de probabilitats d'escenaris Godet: "
                    f"{' + '.join(str(p) for p in scenario_probs)} → {eina_scenario_avg}%."
                ),
                "formula": "mean(scenario.probability)",
                "sources": scenario_sources,
            }

        if blended_return is not None and ext_return is not None and eina_confidence is not None:
            number_explanations["blended_return_index"] = {
                "value": blended_return,
                "because": (
                    f"Combinació ponderada: {ext_return}×{1 - w:.2f} + {eina_confidence}×{w:.2f} = {blended_return}."
                ),
                "formula": "external_return×(1-w) + eina_confidence×w",
                "sources": ext_return_sources + conf_sources,
            }
        elif blended_return is not None:
            number_explanations["blended_return_index"] = {
                "value": blended_return,
                "because": "Només una font disponible; no s'ha aplicat blend.",
                "formula": "single_source",
                "sources": ext_return_sources or conf_sources,
            }

        if blended_risk is not None and ext_risk is not None and eina_risk_proxy is not None:
            number_explanations["blended_risk_index"] = {
                "value": blended_risk,
                "because": (
                    f"Proxy risc EINA = 100 − confiança ({eina_confidence}%) = {eina_risk_proxy}. "
                    f"Blend: {ext_risk}×{1 - w:.2f} + {eina_risk_proxy}×{w:.2f} = {blended_risk}."
                ),
                "formula": "external_risk×(1-w) + (100-confidence)×w",
                "sources": ext_risk_sources + conf_sources,
            }

        alignments: list[dict[str, Any]] = []
        divergences: list[dict[str, Any]] = []
        reasoning: list[dict[str, Any]] = []

        iw = metrics.get("investwatch_summary") or {}
        avg_ret = iw.get("avg_return_score")
        avg_risk = iw.get("avg_risk_score")
        signal = iw.get("signal")

        if signal == "more_return_than_risk" and eina_confidence is not None and eina_confidence >= 55:
            alignments.append(
                {
                    "summary": "Retorn del informe i confiança EINA van en la mateixa direcció (positiva).",
                    "because": (
                        f"L'informe té retorn mitjà {avg_ret}/7 > risc mitjà {avg_risk}/7 (senyal InvestWatch). "
                        f"EINA té confiança mitjana {eina_confidence}% (≥ 55%)."
                    ),
                    "sources": ext_return_sources + conf_sources,
                }
            )
        if signal == "more_risk_than_return":
            tense = [sc for sc in scenario_rows if sc.get("type") in ("inferno", "tension", "infern", "tensio")]
            tense_names = ", ".join(sc.get("name", "?") for sc in tense[:3]) or "escenaris de tensió/alta incertesa"
            divergences.append(
                {
                    "summary": "L'informe pondera més risc que retorn.",
                    "because": (
                        f"Retorn mitjà {avg_ret}/7 ≤ risc mitjà {avg_risk}/7 al text extret. "
                        f"Convé contrastar amb {tense_names} del cas."
                    ),
                    "sources": ext_risk_sources + scenario_sources[:3],
                }
            )

        recs_ext = [metrics.get("primary_recommendation")] if metrics.get("primary_recommendation") else []
        recs_eina = [r.get("type", "").upper() for r in inv_recs]
        if recs_ext and recs_eina:
            ext_rec = recs_ext[0]
            eina_rec = recs_eina[0]
            entry = {
                "summary": (
                    f"Recomanació alineada: {ext_rec} (informe) = {eina_rec} (EINA)."
                    if ext_rec in eina_rec or eina_rec in ext_rec
                    else f"Recomanació divergent: {ext_rec} (informe) vs {eina_rec} (EINA)."
                ),
                "because": (
                    f"Recomanació principal de l'informe: '{ext_rec}'; "
                    f"recomanació EINA: '{eina_rec}' (confiança {inv_recs[0].get('confidence_pct')}%)."
                ),
                "sources": [
                    _source("informe_extern", "recommendations[0]", ext_rec),
                    _source(
                        "eina_investments",
                        "recommendations[0].type",
                        eina_rec,
                        excerpt=inv_recs[0].get("rationale") or "",
                    ),
                ],
            }
            if ext_rec in eina_rec or eina_rec in ext_rec:
                alignments.append(entry)
            else:
                divergences.append(entry)

        policy_companies = eina.get("policy_companies") or []
        matched_cos = self._policy_company_matches(
            metrics, policy_companies, focus_company=focus_company
        )
        if matched_cos:
            names = ", ".join(c["name"] for c in matched_cos[:3])
            alignments.append(
                {
                    "summary": f"Empresa de l'informe vinculada al mapa EINA: {names}.",
                    "because": (
                        "Coincidència per nom d'empresa o ticker al mapa Policy×Indústria "
                        "(no per lletres aïllades del text)."
                    ),
                    "sources": [
                        _source("eina_policy_industry", "companies", c["name"], label=c["name"])
                        for c in matched_cos[:3]
                    ],
                }
            )

        if focus_company:
            from services.actor_impact_utils import canonical_actor

            focus_key = canonical_actor(focus_company).lower()
            matched = [
                c
                for c in policy_companies
                if canonical_actor(c.get("name", "")).lower() == focus_key
                or focus_key in (c.get("name") or "").lower()
            ]
            if matched:
                co = matched[0]
                alignments.append(
                    {
                        "summary": f"Focus empresa: {co['name']} ({co.get('region', '—')}) al mapa EINA.",
                        "because": co.get("why") or "Empresa seleccionada del registre del cas.",
                        "sources": [
                            _source(
                                "eina_policy_industry",
                                "focus_company",
                                co["name"],
                                label=co["name"],
                            )
                        ],
                    }
                )
            else:
                reasoning.append(
                    {
                        "id": "focus_company",
                        "conclusion": f"Focus {focus_company}: sense entrada directa al mapa industrial.",
                        "because": (
                            "El creuament usa escenaris i inversions globals del cas; "
                            "afegeix OSINT o enriqueix Policy×Indústria per vincular l'empresa."
                        ),
                        "formula": "",
                        "sources": [],
                    }
                )

        for key, expl in number_explanations.items():
            reasoning.append(
                {
                    "id": key,
                    "conclusion": f"{key.replace('_', ' ')}: {expl['value']}",
                    "because": expl["because"],
                    "formula": expl.get("formula", ""),
                    "sources": expl.get("sources", []),
                }
            )

        conclusions: list[str] = []
        for r in reasoning[:5]:
            conclusions.append(f"{r['conclusion']} — Per què: {r['because']}")

        if not conclusions and not external_evidence:
            conclusions.append(
                "No hi ha prou dades extretes. Enganxa puntuacions 1-7, percentatges o recomanacions "
                "literalment presents al informe PRAAMS/research."
            )
        elif not conclusions:
            conclusions.append(
                f"S'han extret {len(external_evidence)} dades de l'informe però el cas encara no té "
                "escenaris o recomanacions EINA per combinar."
            )

        suggested_actions = self._build_suggested_actions(
            metrics,
            eina,
            focus_company=focus_company,
            policy_companies=policy_companies,
            report_context=report_context,
        )

        from services.crossover_recommendation_service import build_tiered_recommendations

        tiered_entity = (
            focus_company
            or (report_context or {}).get("reference_entity")
            or (report_context or {}).get("resolved_company")
            or (
                metrics.get("company_name")
                if is_valid_company_name(metrics.get("company_name"))
                else None
            )
        )
        tiered = build_tiered_recommendations(
            metrics,
            eina,
            entity_name=tiered_entity,
            report_context=report_context,
            registry_companies=registry_companies,
            final_numbers=final_numbers,
            divergences=divergences,
            alignments=alignments,
        )

        if suggested_actions:
            for act in suggested_actions[:3]:
                conclusions.append(f"Acció suggerida ({act['action']}): {act['because']}")

        suggested_actions = self._enrich_suggested_actions(suggested_actions)

        from services.investwatch_report_view import build_investwatch_report_view

        investwatch_report = build_investwatch_report_view(
            metrics,
            report_context=report_context,
            crossover={
                "tiered_recommendations": tiered,
                "final_numbers": final_numbers,
                "final_numbers_explanations": number_explanations,
            },
            title=(report_context or {}).get("title") or "",
        )

        parse_warning = metrics.get("parse_warning")
        note = (
            "Creuament basat en dades estructurades (InvestWatch 1-7, mètriques clau filtrades, "
            "recomanació principal) + context EINA. La narrativa pot usar IA només si el parser no n'ha extret prou."
        )
        if parse_warning:
            note += f" Avís: {parse_warning}"

        external_entity = (
            (report_context or {}).get("reference_entity")
            or (report_context or {}).get("resolved_company")
            or focus_company
            or (
                metrics.get("company_name")
                if is_valid_company_name(metrics.get("company_name"))
                else None
            )
        )
        scope_note = (
            f"Dades externes referenciades a «{external_entity}». "
            f"ICG_cas = marc geopolític compartit"
            + (
                f" ({computed_conf.get('case_geopolitical_confidence_index') or computed_conf.get('geopolitical_confidence_index')}%). "
                f"ICE = confiança específica de «{external_entity}»"
                + (
                    f" ({computed_conf.get('entity_confidence_index')}%, "
                    f"Δ {computed_conf.get('entity_icg_delta'):+.1f} pp vs cas)."
                    if computed_conf.get("entity_confidence_index") is not None
                    and computed_conf.get("entity_icg_delta") is not None
                    else "."
                )
                if computed_conf.get("entity_confidence_index") is not None
                else ". Context EINA (escenaris Godet, SMIC, inversions, Policy×Indústria) és de tot el cas."
            )
            if external_entity
            else "Context EINA de tot el cas; l'informe extern no té entitat vinculada explícitament."
        )

        tense_scenarios = [
            s.get("name")
            for s in scenario_rows
            if (s.get("type") or "").lower() in ("inferno", "tension", "infern", "tensio")
        ]
        posture = computed_conf.get("investment_posture") or {}
        from services.geo_intelligence_service import GeoIntelligenceService

        eina_case_summary = GeoIntelligenceService(self.db).eina_case_summary_from_bundle(computed_conf)
        eina_case_summary.update(
            {
                "investment_recommendation": posture.get("recommendation")
                or ((inv_recs[0].get("type") or "HOLD").upper() if inv_recs else None),
                "investment_confidence_pct": posture.get("confidence_pct")
                if posture.get("confidence_pct") is not None
                else (inv_recs[0].get("confidence_pct") if inv_recs else None),
                "investment_rationale": posture.get("rationale")
                or ((inv_recs[0].get("rationale") or "")[:220] if inv_recs else ""),
                "investment_posture_source": posture.get("source"),
                "eina_confidence_pct": computed_conf.get("entity_confidence_index")
                or computed_conf.get("geopolitical_confidence_index")
                or computed_conf.get("confidence_pct")
                or eina_confidence,
                "investment_posture_detail": computed_conf.get("investment_posture_detail"),
                "scenario_count": len(scenario_rows),
                "tense_scenarios": tense_scenarios[:4],
                "policy_companies_count": len(policy_companies),
            }
        )

        return {
            "methodology": "structured_rule_based",
            "scope_note": scope_note,
            "external_entity": external_entity,
            "eina_scope": "case_baseline_plus_entity" if focus_company else "whole_case",
            "llm_used_in_conclusions": bool((report_context or {}).get("narrative_source") == "llm"),
            "llm_data_ignored": llm_stored,
            "parse_mode": metrics.get("parse_mode"),
            "note": note
            + (" Dades LLM emmagatzemades ignorades en aquest crossover." if llm_stored else ""),
            "external_evidence": external_evidence,
            "eina_evidence": eina_evidence,
            "alignments": alignments,
            "divergences": divergences,
            "reasoning": reasoning,
            "final_numbers": final_numbers,
            "final_numbers_explanations": number_explanations,
            "conclusions": conclusions,
            "suggested_actions": suggested_actions,
            "tiered_recommendations": tiered,
            "investwatch_report": investwatch_report,
            "eina_case_summary": eina_case_summary,
        }

    async def ingest_text(
        self,
        case_id: int,
        text: str,
        *,
        source: str = "custom",
        title: str = "",
        source_url: str = "",
        filename: str = "",
        user_id: int | None = None,
        enrich_llm: bool = False,
        reference_entity: str | None = None,
    ) -> dict[str, Any]:
        parsed = parse_financial_document(text, source=source, title=title or filename or source)
        metrics = parsed.get("metrics") or {}
        from services.financial_document_service import apply_reference_entity, preview_parse

        if reference_entity:
            apply_reference_entity(
                metrics,
                reference_entity,
                source="user",
                text=text,
                title=title or filename or source,
            )
        llm_enriched = False
        if enrich_llm:
            from services.financial_document_service import enrich_metrics_with_llm

            metrics = await enrich_metrics_with_llm(text, source, metrics)
            llm_enriched = "llm_extracted" in metrics

        row = CaseExternalReport(
            case_id=case_id,
            user_id=user_id,
            source=source,
            title=title or filename or source,
            source_url=source_url,
            filename=filename,
            raw_text=text[:500_000],
            parsed_metrics=metrics,
            parse_status=parsed.get("parse_status", "partial"),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        preview = preview_parse(
            text,
            source=source,
            title=title or filename or source,
            focus_company=reference_entity or metrics.get("company_name"),
        )
        return {
            "report_id": row.id,
            "parse_status": row.parse_status,
            "metrics": _metrics_without_llm(metrics),
            "reference_entity": metrics.get("reference_entity"),
            "metrics_rule_based_only": True,
            "llm_enriched": llm_enriched,
            "llm_note": (
                "Dades LLM desades per referència però NO s'utilitzen al crossover ni conclusions."
                if llm_enriched
                else None
            ),
            "char_count": parsed.get("char_count", len(text)),
            "preview": preview,
        }

    def preview_text(
        self,
        text: str,
        *,
        source: str = "custom",
        title: str = "",
        focus_company: str | None = None,
    ) -> dict[str, Any]:
        from services.financial_document_service import preview_parse

        return preview_parse(text, source=source, title=title, focus_company=focus_company)

    async def cross_reference(
        self,
        case_id: int,
        *,
        report_id: int | None = None,
        inline_text: str | None = None,
        source: str = "custom",
        external_weight: float = 0.35,
        enrich_llm: bool = False,
        interpret_narrative: str = "auto",
        focus_company: str | None = None,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        import time

        from observability.metrics import FINANCIAL_CROSSOVER_DURATION_SECONDS

        t0 = time.perf_counter()
        try:
            return await self._cross_reference_impl(
                case_id,
                report_id=report_id,
                inline_text=inline_text,
                source=source,
                external_weight=external_weight,
                enrich_llm=enrich_llm,
                interpret_narrative=interpret_narrative,
                focus_company=focus_company,
                project_id=project_id,
            )
        finally:
            FINANCIAL_CROSSOVER_DURATION_SECONDS.observe(time.perf_counter() - t0)

    async def _cross_reference_impl(
        self,
        case_id: int,
        *,
        report_id: int | None = None,
        inline_text: str | None = None,
        source: str = "custom",
        external_weight: float = 0.35,
        enrich_llm: bool = False,
        interpret_narrative: str = "auto",
        focus_company: str | None = None,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        external_block: dict[str, Any]
        raw_text = ""
        report_title = ""
        if report_id:
            r = await self.db.execute(
                select(CaseExternalReport).where(
                    CaseExternalReport.id == report_id,
                    CaseExternalReport.case_id == case_id,
                )
            )
            report = r.scalar_one_or_none()
            if not report:
                return {"found": False, "error": "Informe no trobat"}
            raw_text = report.raw_text or ""
            report_title = report.title or ""
            stored_metrics = dict(report.parsed_metrics or {})
            stored_ref = stored_metrics.get("reference_entity")
            if raw_text.strip():
                fresh = parse_financial_document(
                    raw_text, source=report.source or source, title=report_title
                )
                metrics = fresh.get("metrics") or {}
                from services.financial_document_service import apply_reference_entity

                if stored_ref:
                    apply_reference_entity(
                        metrics,
                        str(stored_ref),
                        source=str(stored_metrics.get("reference_entity_source") or "stored"),
                        text=raw_text,
                        title=report_title,
                    )
                elif focus_company:
                    apply_reference_entity(
                        metrics, focus_company, source="user_focus", text=raw_text, title=report_title
                    )
                else:
                    sanitize_parsed_metrics(metrics, text=raw_text, title=report_title)
                if report_title:
                    from services.financial_document_service import detect_companies_in_text

                    title_hits = detect_companies_in_text(raw_text, title=report_title)
                    merged = {d["name"]: d for d in (metrics.get("detected_companies") or [])}
                    for hit in title_hits:
                        merged.setdefault(hit["name"], hit)
                    metrics["detected_companies"] = sorted(
                        merged.values(), key=lambda x: -x.get("score", 0)
                    )[:6]
                    if not metrics.get("company_name") and metrics["detected_companies"]:
                        metrics["company_name"] = metrics["detected_companies"][0]["name"]
            else:
                metrics = stored_metrics
            external_block = {
                "report_id": report.id,
                "source": report.source,
                "title": report.title,
                "metrics": metrics,
                "parse_status": report.parse_status,
            }
        elif inline_text and len(inline_text.strip()) >= 50:
            raw_text = inline_text.strip()
            parsed = parse_financial_document(raw_text, source=source)
            metrics = parsed.get("metrics") or {}
            from services.financial_document_service import apply_reference_entity

            if focus_company:
                apply_reference_entity(metrics, focus_company, source="user_focus", text=raw_text)
            else:
                sanitize_parsed_metrics(metrics, text=raw_text)
            if enrich_llm:
                from services.financial_document_service import enrich_metrics_with_llm

                metrics = await enrich_metrics_with_llm(inline_text, source, metrics)
            external_block = {"source": source, "metrics": metrics, "parse_status": parsed.get("parse_status")}
        else:
            return {"found": False, "error": "Cal report_id o text inline (mín. 50 caràcters)"}

        metrics = external_block.get("metrics") or {}
        report_context = await self._resolve_report_context(
            case_id,
            metrics,
            focus_company=focus_company or metrics.get("reference_entity"),
            title=report_title,
            project_id=project_id,
        )
        report_context = await self._enrich_report_context_narrative(
            report_context,
            metrics,
            raw_text=raw_text,
            title=report_title,
            interpret_narrative=interpret_narrative,
        )
        from services.company_registry_service import load_company_registry

        registry = await load_company_registry(self.db, case_id, project_id=project_id)
        registry_companies = registry.get("companies") or []

        effective_focus = (
            focus_company
            or metrics.get("reference_entity")
            or report_context.get("resolved_company")
        )

        eina = await self._eina_metrics(
            case_id, project_id=project_id, focus_company=effective_focus
        )
        eina["computed_confidence"] = await self._compute_eina_confidence(
            case_id,
            eina,
            focus_company=effective_focus,
            external_metrics=metrics if effective_focus else None,
        )
        snapshot = eina["computed_confidence"].get("actor_impact_snapshot")
        if snapshot:
            eina["actor_impact"] = snapshot
        crossover = self._build_crossover(
            external_block,
            eina,
            external_weight=external_weight,
            focus_company=effective_focus,
            report_context=report_context,
            registry_companies=registry_companies,
        )

        return {
            "found": True,
            "case_id": case_id,
            "focus_company": effective_focus,
            "reference_entity": metrics.get("reference_entity") or effective_focus,
            "project_id": project_id or eina.get("project_id"),
            "report_context": report_context,
            "crossover_scope": {
                "external_entity": effective_focus,
                "external_entity_source": metrics.get("reference_entity_source")
                or report_context.get("resolution_source"),
                "eina_scope": "case_baseline_plus_entity" if effective_focus else "whole_case",
                "note": crossover.get("scope_note"),
            },
            "external": {
                **external_block,
                "metrics": _metrics_without_llm(external_block.get("metrics") or {}),
            },
            "eina": eina,
            "crossover": crossover,
        }

    async def list_reports(self, case_id: int) -> list[dict[str, Any]]:
        r = await self.db.execute(
            select(CaseExternalReport)
            .where(CaseExternalReport.case_id == case_id)
            .order_by(CaseExternalReport.created_at.desc())
        )
        return [
            {
                "id": row.id,
                "source": row.source,
                "title": row.title,
                "filename": row.filename,
                "source_url": row.source_url,
                "parse_status": row.parse_status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "reference_entity": (row.parsed_metrics or {}).get("reference_entity"),
                "company_name": (row.parsed_metrics or {}).get("company_name"),
                "suggested_ticker": (row.parsed_metrics or {}).get("suggested_ticker")
                or (row.parsed_metrics or {}).get("primary_ticker"),
                "reference_entity_source": (row.parsed_metrics or {}).get("reference_entity_source"),
                "metrics_preview": {
                    "return_factors": len((row.parsed_metrics or {}).get("return_factors") or []),
                    "risk_factors": len((row.parsed_metrics or {}).get("risk_factors") or []),
                },
            }
            for row in r.scalars().all()
        ]
