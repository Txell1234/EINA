"""Financial layer for inquiries — full crossover or lite policy×investment blend."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.investments import InvestmentRecommendation
from services.financial_crossover_service import FinancialCrossoverService
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

        crossover = {
            "methodology": "lite_policy_investment",
            "llm_used_in_conclusions": False,
            "alignments": [],
            "divergences": [],
            "final_numbers": {
                "eina_investment_confidence_avg": avg_conf,
                "policy_companies_mapped": len(companies),
                "blended_return_index": avg_conf,
            },
            "final_numbers_explanations": {},
            "conclusions": [],
            "reasoning": [],
        }

        if avg_conf is not None:
            crossover["final_numbers_explanations"]["blended_return_index"] = {
                "value": avg_conf,
                "because": (
                    f"Lite crossover: mitjana confiança {len(confs)} recomanacions d'inversió EINA "
                    f"({', '.join(str(c) for c in confs)})."
                ),
                "formula": "mean(investment.confidence_pct)",
                "sources": [{"origin": "eina_investments", "field": "confidence_pct"}],
            }
            crossover["conclusions"].append(
                f"Confiança mitjana inversions EINA: {avg_conf}% (sense informe extern)."
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
            "crossover": crossover,
        }
