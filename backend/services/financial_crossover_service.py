"""Cross-reference external financial reports with EINA case conclusions and probabilities."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.external_report import CaseExternalReport
from models.investments import InvestmentRecommendation
from models.prospective import ProspectiveProject, ProspectiveScenario
from services.financial_document_service import parse_financial_document
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


class FinancialCrossoverService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_project(self, case_id: int) -> ProspectiveProject | None:
        r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    async def _eina_metrics(self, case_id: int) -> dict[str, Any]:
        from services.prospective_service import ProspectiveService

        project = await self._resolve_project(case_id)
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
        out["policy_companies"] = [
            {
                "name": c["name"],
                "region": c.get("region"),
                "why": c.get("beneficiary_rationale", "")[:200],
            }
            for c in (policy.get("companies") or [])[:12]
        ]

        return out

    def _collect_external_evidence(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for factor in metrics.get("return_factors") or []:
            evidence.append(
                {
                    "kind": "return_factor",
                    "label": factor.get("label", ""),
                    "value": f"{factor.get('score')}/7",
                    "origin": "informe_extern",
                    "because": f"Extret del text de l'informe (puntuació {factor.get('score')}/7).",
                }
            )
        for factor in metrics.get("risk_factors") or []:
            evidence.append(
                {
                    "kind": "risk_factor",
                    "label": factor.get("label", ""),
                    "value": f"{factor.get('score')}/7",
                    "origin": "informe_extern",
                    "because": f"Extret del text de l'informe (puntuació {factor.get('score')}/7).",
                }
            )
        for pct in metrics.get("percentages") or []:
            evidence.append(
                {
                    "kind": "percentage",
                    "label": pct.get("label", ""),
                    "value": f"{pct.get('value_pct')}%",
                    "origin": "informe_extern",
                    "because": "Percentatge detectat per regex al text enganxat/pujat.",
                }
            )
        for prob in metrics.get("probabilities") or []:
            evidence.append(
                {
                    "kind": "probability",
                    "label": prob.get("label", ""),
                    "value": f"{prob.get('value_pct')}%",
                    "origin": "informe_extern",
                    "because": "Probabilitat detectada per regex al text enganxat/pujat.",
                }
            )
        for rec in metrics.get("recommendations") or []:
            evidence.append(
                {
                    "kind": "recommendation",
                    "label": "Recomanació",
                    "value": rec,
                    "origin": "informe_extern",
                    "because": "Paraula clau BUY/HOLD/SELL trobada literalment al text.",
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
                    "because": "Calculat com a mitjana aritmètica de les puntuacions 1-7 extretes (no LLM).",
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
        for key, val in (smic.get("initial_probs") or {}).items():
            evidence.append(
                {
                    "kind": "smic",
                    "label": str(key),
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
        pcts = metrics.get("percentages") or []
        ret_pcts = [p for p in pcts if any(k in (p.get("label") or "").lower() for k in ("return", "retorn", "yield"))]
        if ret_pcts:
            val = float(ret_pcts[0]["value_pct"])
            return val, [
                _source(
                    "informe_extern",
                    "percentages[0]",
                    val,
                    label=ret_pcts[0].get("label", "Percentatge retorn"),
                )
            ]
        return None, []

    def _build_crossover(
        self,
        external: dict[str, Any],
        eina: dict[str, Any],
        *,
        external_weight: float = 0.35,
    ) -> dict[str, Any]:
        raw_metrics = external.get("metrics") or external
        metrics = _metrics_without_llm(raw_metrics)
        llm_stored = "llm_extracted" in raw_metrics

        ext_risk, ext_risk_sources = self._external_implied_risk(metrics)
        ext_return, ext_return_sources = self._external_implied_return(metrics)

        inv_recs = eina.get("investment_recommendations") or []
        inv_confs = [float(r["confidence_pct"]) for r in inv_recs if r.get("confidence_pct") is not None]
        eina_confidence = _avg(inv_confs)
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

        smic_probs = (eina.get("smic") or {}).get("initial_probs") or {}
        smic_values = [float(v) for v in smic_probs.values() if isinstance(v, (int, float))]

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
            "eina_scenario_probability_avg": eina_scenario_avg,
            "smic_probability_sum": round(sum(smic_values), 2) if smic_values else None,
            "blended_return_index": blended_return,
            "blended_risk_index": blended_risk,
            "external_weight_used": w,
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
            number_explanations["eina_investment_confidence_avg"] = {
                "value": eina_confidence,
                "because": (
                    f"Mitjana de {len(inv_confs)} valors de confiança de recomanacions EINA: "
                    f"{' + '.join(str(c) for c in inv_confs)} → {eina_confidence}%."
                ),
                "formula": "mean(confidence_pct)",
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

        recs_ext = metrics.get("recommendations") or []
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
                    f"Paraula '{ext_rec}' trobada literalment a l'informe; "
                    f"recomanació EINA registrada com '{eina_rec}' (confiança {inv_recs[0].get('confidence_pct')}%."
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

        tickers = metrics.get("tickers_mentioned") or []
        policy_companies = eina.get("policy_companies") or []
        policy_names = {c["name"].upper(): c for c in policy_companies}
        overlap_details: list[dict[str, Any]] = []
        for t in tickers:
            for name_upper, co in policy_names.items():
                if t in name_upper or name_upper.startswith(t):
                    overlap_details.append({"ticker": t, "company": co["name"], "region": co.get("region")})
        if overlap_details:
            names = ", ".join(f"{o['ticker']}↔{o['company']}" for o in overlap_details[:5])
            alignments.append(
                {
                    "summary": f"Coincidència ticker/empresa amb Policy×Indústria: {names}.",
                    "because": (
                        "Tickers en majúscules del text de l'informe coincideixen amb noms d'empresa "
                        "del mapa Policy×Indústria del cas (matching literal, sense inferència)."
                    ),
                    "sources": [
                        _source("informe_extern", "tickers_mentioned", o["ticker"])
                        for o in overlap_details[:5]
                    ]
                    + [
                        _source("eina_policy_industry", "companies", o["company"], label=o["company"])
                        for o in overlap_details[:5]
                    ],
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

        return {
            "methodology": "deterministic_rule_based",
            "llm_used_in_conclusions": False,
            "llm_data_ignored": llm_stored,
            "note": (
                "Les conclusions es basen només en dades extretes del text (regex) i registres EINA del cas. "
                "Cap interpretació generada per LLM."
                + (" Dades LLM emmagatzemades ignorades en aquest crossover." if llm_stored else "")
            ),
            "external_evidence": external_evidence,
            "eina_evidence": eina_evidence,
            "alignments": alignments,
            "divergences": divergences,
            "reasoning": reasoning,
            "final_numbers": final_numbers,
            "final_numbers_explanations": number_explanations,
            "conclusions": conclusions,
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
    ) -> dict[str, Any]:
        parsed = parse_financial_document(text, source=source)
        metrics = parsed.get("metrics") or {}
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
        return {
            "report_id": row.id,
            "parse_status": row.parse_status,
            "metrics": _metrics_without_llm(metrics),
            "metrics_rule_based_only": True,
            "llm_enriched": llm_enriched,
            "llm_note": (
                "Dades LLM desades per referència però NO s'utilitzen al crossover ni conclusions."
                if llm_enriched
                else None
            ),
            "char_count": parsed.get("char_count", len(text)),
        }

    async def cross_reference(
        self,
        case_id: int,
        *,
        report_id: int | None = None,
        inline_text: str | None = None,
        source: str = "custom",
        external_weight: float = 0.35,
        enrich_llm: bool = False,
    ) -> dict[str, Any]:
        external_block: dict[str, Any]
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
            external_block = {
                "report_id": report.id,
                "source": report.source,
                "title": report.title,
                "metrics": report.parsed_metrics or {},
                "parse_status": report.parse_status,
            }
        elif inline_text and len(inline_text.strip()) >= 50:
            parsed = parse_financial_document(inline_text, source=source)
            metrics = parsed.get("metrics") or {}
            if enrich_llm:
                from services.financial_document_service import enrich_metrics_with_llm

                metrics = await enrich_metrics_with_llm(inline_text, source, metrics)
            external_block = {"source": source, "metrics": metrics, "parse_status": parsed.get("parse_status")}
        else:
            return {"found": False, "error": "Cal report_id o text inline (mín. 50 caràcters)"}

        eina = await self._eina_metrics(case_id)
        crossover = self._build_crossover(external_block, eina, external_weight=external_weight)

        return {
            "found": True,
            "case_id": case_id,
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
                "metrics_preview": {
                    "return_factors": len((row.parsed_metrics or {}).get("return_factors") or []),
                    "risk_factors": len((row.parsed_metrics or {}).get("risk_factors") or []),
                },
            }
            for row in r.scalars().all()
        ]
