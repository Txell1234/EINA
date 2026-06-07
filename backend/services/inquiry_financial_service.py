"""Financial layer for inquiries — full crossover or lite policy×investment blend."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.investments import InvestmentRecommendation
from services.financial_crossover_service import FinancialCrossoverService
from services.geo_intelligence_service import GeoIntelligenceService
from services.policy_industry_service import PolicyIndustryService


class InquiryFinancialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _investment_summary(self, case_id: int) -> list[dict[str, Any]]:
        r = await self.db.execute(
            select(InvestmentRecommendation)
            .where(InvestmentRecommendation.case_id == case_id)
            .order_by(InvestmentRecommendation.created_at.desc())
            .limit(5)
        )
        out = []
        for rec in r.scalars().all():
            rtype = rec.recommendation_type
            out.append(
                {
                    "type": rtype.value if hasattr(rtype, "value") else str(rtype),
                    "confidence_pct": rec.confidence_percentage,
                }
            )
        return out

    async def run(
        self,
        case_id: int,
        *,
        question: str,
        financial_text: str = "",
        source: str = "inquiry",
    ) -> dict[str, Any]:
        """Always returns a financial block — full crossover if text, else lite."""
        if (financial_text or "").strip():
            return await FinancialCrossoverService(self.db).cross_reference(
                case_id,
                inline_text=financial_text.strip(),
                source=source,
            )

        policy = await PolicyIndustryService(self.db).build_map(case_id, premise=question)
        investments = await self._investment_summary(case_id)
        confs = [float(i["confidence_pct"]) for i in investments if i.get("confidence_pct") is not None]
        avg_conf = round(sum(confs) / len(confs), 1) if confs else None
        companies = policy.get("companies") or []

        geo_svc = GeoIntelligenceService(self.db)
        geo_bundle = await geo_svc.build_bundle_for_case(case_id)
        eina_summary = geo_svc.eina_case_summary_from_bundle(geo_bundle)
        icg = geo_bundle.get("geopolitical_confidence_index")
        posture = geo_bundle.get("investment_posture") or {}
        posture_src = posture.get("source")
        blend_value = icg if icg is not None else avg_conf
        blend_source = "geopolitical_confidence_index" if icg is not None else "investment_avg"

        crossover = {
            "methodology": "lite_policy_investment_icg",
            "llm_used_in_conclusions": False,
            "alignments": [],
            "divergences": [],
            "final_numbers": {
                "eina_investment_confidence_avg": icg if icg is not None else avg_conf,
                "geopolitical_confidence_index": icg,
                "investment_posture_confidence": avg_conf,
                "policy_companies_mapped": len(companies),
                "blended_return_index": blend_value,
            },
            "final_numbers_explanations": {},
            "conclusions": [],
            "reasoning": [],
            "eina_case_summary": eina_summary,
        }

        if icg is not None:
            crossover["final_numbers_explanations"]["blended_return_index"] = {
                "value": icg,
                "because": geo_bundle.get("confidence_detail") or f"ICG {icg}% (lite inquiry, sense informe extern).",
                "formula": geo_bundle.get("geopolitical_confidence_formula")
                or "ICG = Σ(value×weight)/Σ(weight)",
                "sources": [{"origin": "eina_geopolitical_confidence", "field": "geopolitical_confidence_index"}],
            }
            crossover["conclusions"].append(f"Confiança geo-estratègica (ICG): {icg}% — mode lite sense informe extern.")
            if posture_src == "default_fallback" and avg_conf is not None:
                crossover["conclusions"].append(
                    f"Postura inversió per defecte: HOLD {avg_conf}% (separada de l'ICG)."
                )
        elif avg_conf is not None:
            crossover["final_numbers_explanations"]["blended_return_index"] = {
                "value": avg_conf,
                "because": (
                    f"Lite crossover: mitjana confiança {len(confs)} recomanacions d'inversió EINA "
                    f"({', '.join(str(c) for c in confs)}). ICG no disponible — executa intel·ligència."
                ),
                "formula": "mean(investment.confidence_pct)",
                "sources": [{"origin": "eina_investments", "field": "confidence_pct"}],
            }
            crossover["conclusions"].append(
                f"Confiança mitjana inversions EINA: {avg_conf}% (ICG pendent — sense dades OSINT)."
            )

        if companies:
            names = ", ".join(c["name"] for c in companies[:5])
            crossover["alignments"].append(
                {
                    "summary": f"Policy×Indústria: {len(companies)} empreses vinculades a la premisa.",
                    "because": f"Mapatge determinista per premisa: {names}.",
                    "sources": [{"origin": "eina_policy_industry", "field": "companies"}],
                }
            )

        return {
            "found": True,
            "mode": "lite",
            "policy_industry": policy,
            "investments": investments,
            "geopolitical_confidence": geo_bundle,
            "crossover": crossover,
            "blend_source": blend_source,
        }
