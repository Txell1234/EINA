"""
Intelligence Unit — readiness status and unified analysis pipeline for a case.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case
from models.extract import ExtractedStatement
from models.geopolitical import DiplomaticEvent, GeopoliticalRisk
from models.investments import InvestmentRecommendation
from models.actor_impact import ActorImpactAssessment
from models.osint import OSINTQuery, OSINTResult
from services.extract_service import ExtractService
from services.osint_data_utils import flatten_osint_items, osint_has_error

logger = logging.getLogger(__name__)


class IntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _count_osint_articles(self, case_id: int) -> tuple[int, int]:
        queries_r = await self.db.execute(select(OSINTQuery).where(OSINTQuery.case_id == case_id))
        queries = list(queries_r.scalars().all())
        article_count = 0
        for q in queries:
            results_r = await self.db.execute(select(OSINTResult).where(OSINTResult.query_id == q.id))
            for r in results_r.scalars().all():
                if r.status == "error" or not isinstance(r.data, dict) or osint_has_error(r.data):
                    continue
                article_count += len(flatten_osint_items(r.data))
        return len(queries), article_count

    async def get_status(self, case_id: int) -> dict[str, Any]:
        case_r = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_r.scalar_one_or_none()
        if not case:
            return {"found": False}

        osint_queries, osint_articles = await self._count_osint_articles(case_id)

        stmt_count = (
            await self.db.execute(
                select(func.count())
                .select_from(ExtractedStatement)
                .where(ExtractedStatement.case_id == case_id)
            )
        ).scalar() or 0

        events_count = (
            await self.db.execute(
                select(func.count())
                .select_from(DiplomaticEvent)
                .where(DiplomaticEvent.case_id == case_id)
            )
        ).scalar() or 0

        risks_count = (
            await self.db.execute(
                select(func.count())
                .select_from(GeopoliticalRisk)
                .where(GeopoliticalRisk.case_id == case_id)
            )
        ).scalar() or 0

        inv_count = (
            await self.db.execute(
                select(func.count())
                .select_from(InvestmentRecommendation)
                .where(InvestmentRecommendation.case_id == case_id)
            )
        ).scalar() or 0

        impact_count = (
            await self.db.execute(
                select(func.count())
                .select_from(ActorImpactAssessment)
                .where(ActorImpactAssessment.case_id == case_id)
            )
        ).scalar() or 0

        from services.llm_service import LLMService

        llm = LLMService(mode="extract")

        steps = {
            "osint": {
                "label": "Recollida OSINT",
                "ready": osint_articles > 0,
                "count": osint_articles,
                "detail": f"{osint_queries} consultes · {osint_articles} articles",
            },
            "extraction": {
                "label": "Extracció de declaracions",
                "ready": stmt_count > 0,
                "count": stmt_count,
                "detail": f"{stmt_count} declaracions",
            },
            "events": {
                "label": "Esdeveniments geopolítics",
                "ready": events_count > 0,
                "count": events_count,
                "detail": f"{events_count} esdeveniments",
            },
            "risks": {
                "label": "Riscos geopolítics",
                "ready": risks_count > 0,
                "count": risks_count,
                "detail": f"{risks_count} països/regions",
            },
            "investment": {
                "label": "Anàlisi d'inversions",
                "ready": inv_count > 0,
                "count": inv_count,
                "detail": f"{inv_count} recomanacions",
            },
            "actor_impact": {
                "label": "Impacte sobre actors",
                "ready": impact_count > 0,
                "count": impact_count,
                "detail": f"{impact_count} avaluacions",
            },
        }

        ready_count = sum(1 for s in steps.values() if s["ready"])
        pipeline_ready = osint_articles > 0 and llm.configured

        return {
            "found": True,
            "case_id": case_id,
            "case_name": case.name,
            "case_type": case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type or "general"),
            "case_status": case.status.value if hasattr(case.status, "value") else str(case.status),
            "llm_configured": llm.configured,
            "steps": steps,
            "ready_steps": ready_count,
            "total_steps": len(steps),
            "pipeline_ready": pipeline_ready,
            "blocker": None
            if pipeline_ready
            else ("no_llm" if not llm.configured else "no_osint"),
        }

    async def _run_extraction(
        self,
        case_id: int,
        *,
        apply_scope: bool = False,
        scope: Any | None = None,
    ) -> dict[str, Any]:
        svc = ExtractService(self.db)
        total_extracted = 0
        skipped = 0
        async for event in svc.extract_from_case(
            case_id, apply_scope=apply_scope, scope=scope
        ):
            ev = event.get("event")
            if ev == "error":
                return {"ok": False, "error": event.get("message", "Error d'extracció")}
            if ev == "start":
                skipped = event.get("skipped_existing", 0)
            if ev == "saved":
                total_extracted = event.get("count", total_extracted)
            if ev == "done":
                total_extracted = event.get("total_extracted", total_extracted)
        return {"ok": True, "extracted": total_extracted, "skipped_existing": skipped}

    async def run_pipeline(
        self,
        case_id: int,
        *,
        include_investment: bool = True,
        auto_cleanup: bool = False,
        apply_scope: bool = False,
    ) -> dict[str, Any]:
        status = await self.get_status(case_id)
        if not status.get("found"):
            return {"ok": False, "error": "Cas no trobat"}
        if status.get("blocker") == "no_llm":
            return {
                "ok": False,
                "error": "Cal configurar OPENAI_API_KEY (o un altre proveïdor LLM) per executar el pipeline.",
                "steps": [],
            }
        if status.get("blocker") == "no_osint":
            return {
                "ok": False,
                "error": "No hi ha articles OSINT. Executa la recollida abans del pipeline.",
                "blocker": "no_osint",
                "steps": [],
            }

        from services.analysis_scope_service import should_auto_apply_scope

        use_scope = apply_scope
        if not use_scope and await should_auto_apply_scope(self.db, case_id):
            use_scope = True

        steps_log: list[dict[str, Any]] = []

        scope = None
        if use_scope:
            from services.analysis_scope_service import resolve_scope_for_case

            scope, _ = await resolve_scope_for_case(self.db, case_id)

        async def step(name: str, label: str, fn) -> bool:
            try:
                result = await fn()
                steps_log.append({"step": name, "label": label, "ok": True, **result})
                return True
            except Exception as exc:
                logger.warning("Intelligence pipeline step %s failed: %s", name, exc)
                steps_log.append({"step": name, "label": label, "ok": False, "error": str(exc)})
                return False

        await step(
            "extraction",
            "Extracció de declaracions",
            lambda: self._run_extraction(case_id, apply_scope=use_scope, scope=scope),
        )

        if auto_cleanup:
            async def cleanup_step():
                svc = ExtractService(self.db)
                return await svc.cleanup_pass(case_id)

            await step("cleanup", "Neteja de declaracions", cleanup_step)

        async def classify():
            from services.ai_classification_service import AIClassificationService

            svc = AIClassificationService(self.db)
            n = await svc.classify_all_case_osint(case_id)
            return {"classified": len(n)}

        await step("classification", "Classificació IA del OSINT", classify)

        async def extract_events():
            from services.diplomatic_event_service import DiplomaticEventService

            svc = DiplomaticEventService(self.db)
            events = await svc.extract_events_from_osint(case_id)
            return {"events_found": len(events)}

        await step("events", "Esdeveniments diplomàtics", extract_events)

        async def calc_risks():
            from services.geopolitical_risk_service import GeopoliticalRiskService

            svc = GeopoliticalRiskService(self.db)
            result = await svc.calculate_risks_from_osint(case_id)
            return {"risks": result.get("risks_calculated", result.get("countries", 0)) if isinstance(result, dict) else 0}

        await step("risks", "Riscos geopolítics", calc_risks)

        async def tavily_research():
            from app.config import settings
            from models.case import Case

            if not (settings.TAVILY_API_KEY or "").strip():
                return {"skipped": True, "reason": "TAVILY_API_KEY no configurada"}
            case_r = await self.db.execute(select(Case).where(Case.id == case_id))
            case = case_r.scalar_one_or_none()
            if not case:
                return {"skipped": True, "reason": "cas no trobat"}
            text = " ".join(
                filter(None, [case.name, getattr(case, "description", None), getattr(case, "hypothesis", None)])
            )
            from services.tavily_osint_service import collect_tavily_for_case

            result = await collect_tavily_for_case(
                self.db,
                case_id,
                text,
                hypothesis=getattr(case, "hypothesis", "") or "",
                run_research=True,
                max_queries=2,
                run_preferred_crawl=False,
            )
            research_runs = [r for r in (result.get("runs") or []) if r.get("kind") == "research"]
            return {
                "status": result.get("status"),
                "research_runs": len(research_runs),
                "articles_collected": result.get("articles_collected", 0),
            }

        await step("tavily_research", "Tavily Research (informe estratègic)", tavily_research)

        async def actor_impact():
            from services.actor_impact_service import ActorImpactService

            svc = ActorImpactService(self.db)
            data = await svc.analyze_and_save(case_id)
            return {
                "actors": len(data.get("actors") or []),
                "claims": len(data.get("claims") or []),
            }

        await step("actor_impact", "Impacte actors × escenaris", actor_impact)

        if include_investment and not status["steps"]["investment"]["ready"]:
            async def investment():
                from services.investment_service import InvestmentService

                svc = InvestmentService(self.db)
                rec = await svc.generate_recommendation(case_id)
                return {"recommendation_id": rec.get("recommendation_id")}

            await step("investment", "Recomanació d'inversió", investment)

        final = await self.get_status(case_id)
        failed = [s for s in steps_log if not s.get("ok")]
        return {
            "ok": len(failed) == 0,
            "steps": steps_log,
            "status": final,
            "message": "Pipeline completat." if not failed else f"Completat amb {len(failed)} pas(s) amb errors.",
        }
