"""Q2FS inquiry orchestrator — question triggers scoped OSINT + intelligence + synthesis."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case, CasePrompt
from models.prospective import ProspectiveProject, ProspectiveScenario, SMICResult
from models.prospective_inquiry import ProspectiveInquiry
from services.analysis_scope_service import merge_scope_into_query_params, resolve_scope_for_case
from services.actor_impact_service import ActorImpactService
from services.inquiry_audit_service import InquiryAuditService
from services.inquiry_compare_service import compare_inquiry_answers, build_case_inquiry_comparison
from services.inquiry_financial_service import InquiryFinancialService
from services.inquiry_monitor_service import InquiryMonitorService
from services.inquiry_scope import build_inquiry_scope
from services.inquiry_wizard_bridge_service import InquiryWizardBridgeService
from services.intelligence_service import IntelligenceService
from services.morph_bootstrap_service import MorphBootstrapService
from services.osint_service import OSINTService
from services.parse_trigger_service import ParseTriggerService
from services.policy_industry_service import PolicyIndustryService
from services.prospective_synthesis_service import ProspectiveSynthesisService

logger = logging.getLogger(__name__)

_STEP_KEYS = (
    "parse",
    "osint",
    "intelligence",
    "policy_industry",
    "financial",
    "morph_bootstrap",
    "monitors",
    "synthesis",
)


class InquiryOrchestratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _audit(self, artifacts: dict[str, Any]) -> InquiryAuditService:
        return InquiryAuditService(artifacts)

    async def prepare_rerun(self, inquiry_id: int) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"ok": False, "error": "Inquiry no trobada"}

        artifacts = self._artifacts(inquiry)
        audit = self._audit(artifacts)
        run_n = audit.begin_run()

        if inquiry.answer:
            history = list(artifacts.get("answer_history") or [])
            history.append(
                {
                    "run_number": run_n - 1 if run_n > 1 else inquiry.run_count or 0,
                    "answer": inquiry.answer,
                    "completed_at": inquiry.completed_at.isoformat() if inquiry.completed_at else None,
                }
            )
            artifacts["answer_history"] = history[-20:]

        inquiry.status = "pending"
        inquiry.error_message = ""
        inquiry.run_count = (inquiry.run_count or 0) + 1
        inquiry.last_rerun_at = datetime.now(timezone.utc)
        artifacts["audit_trail"] = audit.trail()
        inquiry.artifacts = artifacts
        await self.db.commit()
        return {"ok": True, "inquiry_id": inquiry.id, "run_number": run_n}

    async def run_batch(self, inquiry_id: int, *, force_refresh: bool = True) -> dict[str, Any]:
        """Non-SSE run for scheduler — collects final status."""
        await self.prepare_rerun(inquiry_id)
        last: dict[str, Any] = {"status": "unknown"}
        async for event in self.run_stream(inquiry_id, force_refresh=force_refresh):
            last = event
        return {
            "status": last.get("status") or last.get("event"),
            "inquiry_id": inquiry_id,
            "event": last.get("event"),
        }

    async def set_schedule(
        self,
        inquiry_id: int,
        *,
        enabled: bool,
        interval_hours: int = 24,
    ) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"ok": False, "error": "Inquiry no trobada"}

        hours = max(1, min(interval_hours, 168))
        inquiry.auto_rerun_enabled = 1 if enabled else 0
        inquiry.rerun_interval_hours = hours
        if enabled:
            inquiry.next_rerun_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        else:
            inquiry.next_rerun_at = None

        artifacts = self._artifacts(inquiry)
        self._audit(artifacts).log_event(
            "schedule_updated",
            {"enabled": enabled, "interval_hours": hours},
        )
        inquiry.artifacts = artifacts
        await self.db.commit()
        return {
            "ok": True,
            "inquiry_id": inquiry.id,
            "auto_rerun_enabled": bool(inquiry.auto_rerun_enabled),
            "rerun_interval_hours": hours,
            "next_rerun_at": inquiry.next_rerun_at.isoformat() if inquiry.next_rerun_at else None,
        }

    async def _schedule_next_if_enabled(self, inquiry: ProspectiveInquiry) -> None:
        if inquiry.auto_rerun_enabled and inquiry.rerun_interval_hours:
            hours = max(1, min(inquiry.rerun_interval_hours or 24, 168))
            inquiry.next_rerun_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    async def _get_inquiry(self, inquiry_id: int) -> ProspectiveInquiry | None:
        r = await self.db.execute(select(ProspectiveInquiry).where(ProspectiveInquiry.id == inquiry_id))
        return r.scalar_one_or_none()

    async def _append_step(self, inquiry: ProspectiveInquiry, step: dict[str, Any]) -> None:
        log = list(inquiry.steps_log or [])
        log.append({**step, "at": datetime.now(timezone.utc).isoformat()})
        inquiry.steps_log = log
        await self.db.commit()

    def _artifacts(self, inquiry: ProspectiveInquiry) -> dict[str, Any]:
        return dict(inquiry.artifacts or {})

    def _step_cache(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        return dict(artifacts.get("step_cache") or {})

    def _cache_step(self, artifacts: dict[str, Any], step: str, payload: dict[str, Any]) -> None:
        cache = self._step_cache(artifacts)
        cache[step] = {**payload, "cached_at": datetime.now(timezone.utc).isoformat()}
        artifacts["step_cache"] = cache

    def _cached(self, artifacts: dict[str, Any], step: str, force_refresh: bool) -> dict[str, Any] | None:
        if force_refresh:
            return None
        hit = self._step_cache(artifacts).get(step)
        return hit if isinstance(hit, dict) else None

    async def _godet_ready(self, case_id: int) -> tuple[bool, list[dict[str, Any]]]:
        r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        project = r.scalar_one_or_none()
        if not project:
            return False, []
        sc_r = await self.db.execute(
            select(ProspectiveScenario).where(ProspectiveScenario.project_id == project.id)
        )
        scenarios = list(sc_r.scalars().all())
        if len(scenarios) < 1:
            return False, []
        ai = await ActorImpactService(self.db).build_assessment(case_id, project.id)
        return True, ai.get("scenarios") or []

    async def _smic_for_case(self, case_id: int) -> dict[str, Any] | None:
        r = await self.db.execute(
            select(ProspectiveProject)
            .where(ProspectiveProject.case_id == case_id)
            .order_by(ProspectiveProject.created_at.desc())
            .limit(1)
        )
        project = r.scalar_one_or_none()
        if not project:
            return None
        smic_r = await self.db.execute(
            select(SMICResult).where(SMICResult.project_id == project.id)
        )
        smic = smic_r.scalar_one_or_none()
        if not smic:
            return None
        return {
            "initial_probs": smic.initial_probs,
            "final_probs": smic.final_probs,
            "final_labels": smic.final_labels,
        }

    async def apply_to_wizard(
        self,
        inquiry_id: int,
        *,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"ok": False, "error": "Inquiry no trobada"}
        morph = (inquiry.artifacts or {}).get("morph_bootstrap")
        if not morph:
            parsed = inquiry.parsed_trigger or {}
            morph = MorphBootstrapService().bootstrap(
                question=inquiry.question,
                event_type=parsed.get("event_type", "geopolitical"),
                actors=parsed.get("actors"),
            )
        result = await InquiryWizardBridgeService(self.db).apply_morph_bootstrap(
            case_id=inquiry.case_id,
            question=inquiry.question,
            morph_bootstrap=morph,
            project_id=project_id,
        )
        if result.get("ok"):
            artifacts = self._artifacts(inquiry)
            artifacts["wizard_project_id"] = result.get("project_id")
            inquiry.artifacts = artifacts
            await self.db.commit()
        return result

    async def apply_monitors(
        self,
        inquiry_id: int,
        *,
        project_id: int,
    ) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"ok": False, "error": "Inquiry no trobada"}
        suggestions = (inquiry.artifacts or {}).get("monitor_suggestions")
        if not suggestions:
            suggestions = InquiryMonitorService().suggest(
                question=inquiry.question,
                parsed_trigger=inquiry.parsed_trigger or {},
                morph_bootstrap=(inquiry.artifacts or {}).get("morph_bootstrap"),
            )
        return await InquiryMonitorService().apply_to_project(
            self.db,
            case_id=inquiry.case_id,
            project_id=project_id,
            suggestions=suggestions,
        )

    async def create_inquiry(
        self,
        case_id: int,
        question: str,
        *,
        mode: str = "full",
        user_id: int | None = None,
        include_financial: bool = False,
        financial_text: str = "",
    ) -> ProspectiveInquiry:
        case_r = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_r.scalar_one_or_none()
        if not case:
            raise ValueError("Cas no trobat")

        parsed = ParseTriggerService().parse(
            question,
            case_name=case.name or "",
            case_description=case.description or "",
        )
        if not parsed.get("ok"):
            raise ValueError(parsed.get("error", "Parse failed"))

        scope = build_inquiry_scope(
            question,
            case_name=case.name or "",
            case_description=case.description or "",
        )
        scope_dict = scope.to_dict()
        scope_dict["case_name"] = case.name
        scope_dict["case_description"] = case.description

        row = ProspectiveInquiry(
            case_id=case_id,
            user_id=user_id,
            question=question.strip(),
            mode=mode if mode in ("full", "lite") else "full",
            status="pending",
            parsed_trigger=parsed,
            inquiry_scope=scope_dict,
            include_financial=1 if include_financial else 0,
            financial_text=financial_text or "",
        )
        self.db.add(row)

        self.db.add(
            CasePrompt(
                case_id=case_id,
                prompt=question.strip(),
                ai_analysis={"source": "prospective_inquiry", "mode": mode},
            )
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def morph_bootstrap_for_inquiry(self, inquiry_id: int) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"found": False, "error": "Inquiry no trobada"}
        parsed = inquiry.parsed_trigger or {}
        return {
            "found": True,
            "inquiry_id": inquiry.id,
            **MorphBootstrapService().bootstrap(
                question=inquiry.question,
                event_type=parsed.get("event_type", "geopolitical"),
                actors=parsed.get("actors"),
            ),
        }

    async def run_stream(
        self,
        inquiry_id: int,
        *,
        force_refresh: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            yield {"event": "error", "message": "Inquiry no trobada"}
            return

        case_id = inquiry.case_id
        scope = build_inquiry_scope(inquiry.question)
        if inquiry.inquiry_scope and isinstance(inquiry.inquiry_scope, dict):
            scope = build_inquiry_scope(
                inquiry.inquiry_scope.get("question", inquiry.question),
                case_name=inquiry.inquiry_scope.get("case_name", ""),
                case_description=inquiry.inquiry_scope.get("case_description", ""),
            )

        artifacts = self._artifacts(inquiry)
        parsed = inquiry.parsed_trigger or {}
        audit = self._audit(artifacts)
        if audit.run_number() == 0:
            audit.begin_run()
            artifacts = audit.artifacts
            inquiry.artifacts = artifacts

        try:
            # --- parse ---
            hit = self._cached(artifacts, "parse", force_refresh)
            if hit:
                yield {"event": "step", "step": "parse", "status": "done", "cached": True, "parsed": parsed}
            else:
                inquiry.status = "parsing"
                await self.db.commit()
                self._cache_step(artifacts, "parse", {"ok": True, "parsed": parsed})
                inquiry.artifacts = artifacts
                await self._append_step(inquiry, {"step": "parse", "ok": True, "cached": False})
                yield {"event": "step", "step": "parse", "status": "done", "parsed": parsed}

            # --- osint ---
            hit = self._cached(artifacts, "osint", force_refresh)
            if hit:
                scope_audit = hit.get("audit") or inquiry.scope_audit or {}
                inquiry.scope_audit = scope_audit
                yield {"event": "step", "step": "osint", "status": "done", "cached": True, "audit": scope_audit}
            else:
                inquiry.status = "osint"
                await self.db.commit()
                yield {"event": "step", "step": "osint", "status": "running"}

                analysis_scope, _ = await resolve_scope_for_case(self.db, case_id)
                osint_svc = OSINTService(self.db)
                scope_audit: dict[str, Any] = {"queries_run": 0, "articles_total": 0}
                queries = scope.osint_queries or [inquiry.question[:80]]
                for q in queries[:3]:
                    for qtype in ("gdelt", "google_news"):
                        params = merge_scope_into_query_params(
                            {"query": q, "days": analysis_scope.period_days or 90},
                            analysis_scope,
                        )
                        try:
                            result = await osint_svc.execute_query(qtype, params, case_id=case_id)
                            scope_audit["queries_run"] += 1
                            data = result.get("data") if isinstance(result, dict) else {}
                            if isinstance(data, dict):
                                sf = data.get("_scope_filter") or {}
                                for k in ("removed_topic", "removed_must_match", "kept", "input"):
                                    if k in sf:
                                        scope_audit[k] = scope_audit.get(k, 0) + int(sf.get(k) or 0)
                        except Exception as exc:
                            logger.warning("OSINT query failed %s: %s", qtype, exc)

                inquiry.scope_audit = scope_audit
                self._cache_step(artifacts, "osint", {"ok": True, "audit": scope_audit})
                inquiry.artifacts = artifacts
                await self._append_step(inquiry, {"step": "osint", "ok": True, **scope_audit})
                yield {"event": "step", "step": "osint", "status": "done", "audit": scope_audit}

            # --- intelligence ---
            hit = self._cached(artifacts, "intelligence", force_refresh)
            if hit:
                pipe = hit.get("pipeline") or artifacts.get("pipeline") or {}
                artifacts["pipeline"] = pipe
                yield {"event": "step", "step": "intelligence", "status": "done", "cached": True, "pipeline": pipe}
            else:
                inquiry.status = "intelligence"
                await self.db.commit()
                yield {"event": "step", "step": "intelligence", "status": "running"}

                pipe = await IntelligenceService(self.db).run_pipeline(
                    case_id, apply_scope=True, include_investment=True
                )
                artifacts["pipeline"] = pipe
                self._cache_step(artifacts, "intelligence", {"ok": pipe.get("ok"), "pipeline": pipe})
                inquiry.artifacts = artifacts
                await self._append_step(
                    inquiry, {"step": "intelligence", "ok": pipe.get("ok"), "steps": pipe.get("steps")}
                )
                yield {"event": "step", "step": "intelligence", "status": "done", "pipeline": pipe}

            # --- policy_industry ---
            hit = self._cached(artifacts, "policy_industry", force_refresh)
            if hit:
                policy_map = hit.get("policy_industry") or artifacts.get("policy_industry") or {}
                artifacts["policy_industry"] = policy_map
                yield {
                    "event": "step",
                    "step": "policy_industry",
                    "status": "done",
                    "cached": True,
                    "companies": len(policy_map.get("companies") or []),
                }
            else:
                yield {"event": "step", "step": "policy_industry", "status": "running"}
                policy_map = await PolicyIndustryService(self.db).build_map(
                    case_id, premise=inquiry.question
                )
                artifacts["policy_industry"] = policy_map
                self._cache_step(
                    artifacts,
                    "policy_industry",
                    {"ok": True, "policy_industry": policy_map, "companies": len(policy_map.get("companies") or [])},
                )
                inquiry.artifacts = artifacts
                await self._append_step(
                    inquiry,
                    {"step": "policy_industry", "ok": True, "companies": len(policy_map.get("companies") or [])},
                )
                yield {
                    "event": "step",
                    "step": "policy_industry",
                    "status": "done",
                    "companies": len(policy_map.get("companies") or []),
                }

            # --- financial (always) ---
            hit = self._cached(artifacts, "financial", force_refresh)
            fin_text = inquiry.financial_text or ""
            if hit and not force_refresh:
                fc = hit.get("financial") or artifacts.get("financial_crossover") or {}
                artifacts["financial_crossover"] = fc
                yield {
                    "event": "step",
                    "step": "financial",
                    "status": "done",
                    "cached": True,
                    "mode": fc.get("mode", "lite"),
                    "found": fc.get("found"),
                }
            else:
                yield {"event": "step", "step": "financial", "status": "running"}
                fc = await InquiryFinancialService(self.db).run(
                    case_id,
                    question=inquiry.question,
                    financial_text=fin_text if inquiry.include_financial else "",
                    source="inquiry",
                )
                artifacts["financial_crossover"] = fc
                self._cache_step(artifacts, "financial", {"ok": fc.get("found"), "financial": fc, "mode": fc.get("mode")})
                inquiry.artifacts = artifacts
                await self._append_step(
                    inquiry, {"step": "financial", "ok": fc.get("found"), "mode": fc.get("mode")}
                )
                yield {
                    "event": "step",
                    "step": "financial",
                    "status": "done",
                    "mode": fc.get("mode"),
                    "found": fc.get("found"),
                }

            # --- morph_bootstrap ---
            hit = self._cached(artifacts, "morph_bootstrap", force_refresh)
            if hit:
                morph = hit.get("morph") or artifacts.get("morph_bootstrap") or {}
                artifacts["morph_bootstrap"] = morph
                yield {
                    "event": "step",
                    "step": "morph_bootstrap",
                    "status": "done",
                    "cached": True,
                    "valid_combinations": morph.get("valid_combinations_count"),
                }
            else:
                yield {"event": "step", "step": "morph_bootstrap", "status": "running"}
                morph = MorphBootstrapService().bootstrap(
                    question=inquiry.question,
                    event_type=parsed.get("event_type", "geopolitical"),
                    actors=parsed.get("actors"),
                )
                artifacts["morph_bootstrap"] = morph
                self._cache_step(
                    artifacts,
                    "morph_bootstrap",
                    {"ok": True, "morph": morph, "valid_combinations": morph.get("valid_combinations_count")},
                )
                inquiry.artifacts = artifacts
                await self._append_step(
                    inquiry,
                    {
                        "step": "morph_bootstrap",
                        "ok": True,
                        "valid_combinations": morph.get("valid_combinations_count"),
                    },
                )
                yield {
                    "event": "step",
                    "step": "morph_bootstrap",
                    "status": "done",
                    "valid_combinations": morph.get("valid_combinations_count"),
                    "godet_preview": morph.get("godet_preview"),
                }

            # --- monitors (suggestions) ---
            hit = self._cached(artifacts, "monitors", force_refresh)
            if hit:
                mon = hit.get("monitors") or artifacts.get("monitor_suggestions") or {}
                artifacts["monitor_suggestions"] = mon
                yield {
                    "event": "step",
                    "step": "monitors",
                    "status": "done",
                    "cached": True,
                    "count": mon.get("count", 0),
                }
            else:
                yield {"event": "step", "step": "monitors", "status": "running"}
                mon = InquiryMonitorService().suggest(
                    question=inquiry.question,
                    parsed_trigger=parsed,
                    morph_bootstrap=artifacts.get("morph_bootstrap"),
                    horizon_label=parsed.get("horizon_label", ""),
                )
                artifacts["monitor_suggestions"] = mon
                self._cache_step(artifacts, "monitors", {"ok": True, "monitors": mon, "count": mon.get("count")})
                inquiry.artifacts = artifacts
                await self._append_step(inquiry, {"step": "monitors", "ok": True, "count": mon.get("count")})
                yield {
                    "event": "step",
                    "step": "monitors",
                    "status": "done",
                    "count": mon.get("count"),
                    "suggested_monitors": mon.get("suggested_monitors"),
                }

            actor_impact = artifacts.get("actor_impact")
            if not actor_impact or force_refresh:
                actor_impact = await ActorImpactService(self.db).build_assessment(case_id)
                artifacts["actor_impact"] = actor_impact
                inquiry.artifacts = artifacts

            godet_ready, scenario_rows = await self._godet_ready(case_id)
            smic_result = await self._smic_for_case(case_id) if godet_ready else None
            inquiry.artifacts = artifacts

            if inquiry.mode == "full" and not godet_ready:
                inquiry.status = "awaiting_godet"
                await self._schedule_next_if_enabled(inquiry)
                audit.log_event("awaiting_godet", {"godet_ready": False})
                artifacts["audit_trail"] = audit.trail()
                inquiry.artifacts = artifacts
                await self.db.commit()
                yield {
                    "event": "awaiting_godet",
                    "message": (
                        "Completa MIC-MAC, MACTOR, morfològic i SMIC a Anàlisi Prospectiva. "
                        "Usa «Aplicar al wizard» per sembrar el pas morfològic. "
                        "Després crida POST /api/prospective/inquiries/{id}/synthesize"
                    ),
                    "morph_bootstrap": artifacts.get("morph_bootstrap"),
                    "monitor_suggestions": artifacts.get("monitor_suggestions"),
                }
                return

            inquiry.status = "synthesizing"
            await self.db.commit()
            yield {"event": "step", "step": "synthesis", "status": "running"}

            answer = ProspectiveSynthesisService().synthesize(
                question=inquiry.question,
                parsed_trigger=parsed,
                actor_impact=actor_impact,
                scenarios=scenario_rows,
                financial_crossover=artifacts.get("financial_crossover"),
                policy_industry=artifacts.get("policy_industry"),
                morph_bootstrap=artifacts.get("morph_bootstrap"),
                monitor_suggestions=artifacts.get("monitor_suggestions"),
                smic_result=smic_result,
                scope_audit=inquiry.scope_audit,
                godet_ready=godet_ready,
            )
            prev_answer = None
            history = artifacts.get("answer_history") or []
            if history:
                prev_answer = history[-1].get("answer")
            diff = compare_inquiry_answers(prev_answer, answer)
            artifacts["answer_diff"] = diff
            audit.log_event("synthesis_completed", {"probability_pct": answer.get("probability_pct")})
            artifacts["audit_trail"] = audit.trail()

            inquiry.answer = answer
            inquiry.status = "completed"
            inquiry.completed_at = datetime.now(timezone.utc)
            self._cache_step(artifacts, "synthesis", {"ok": True, "answer": answer})
            inquiry.artifacts = artifacts
            await self._schedule_next_if_enabled(inquiry)
            await self.db.commit()
            await self._append_step(inquiry, {"step": "synthesis", "ok": True})

            yield {
                "event": "done",
                "inquiry_id": inquiry.id,
                "status": "completed",
                "answer": answer,
                "answer_diff": diff,
            }

        except Exception as exc:
            logger.exception("Inquiry %s failed: %s", inquiry_id, exc)
            audit = self._audit(self._artifacts(inquiry))
            audit.log_event("run_failed", {"error": str(exc)[:200]})
            inquiry.artifacts = audit.artifacts
            inquiry.status = "failed"
            inquiry.error_message = str(exc)[:500]
            await self.db.commit()
            yield {"event": "error", "message": str(exc)}

    async def synthesize(self, inquiry_id: int) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"found": False, "error": "Inquiry no trobada"}

        godet_ready, scenario_rows = await self._godet_ready(inquiry.case_id)
        artifacts = self._artifacts(inquiry)
        actor_impact = artifacts.get("actor_impact")
        if not actor_impact:
            actor_impact = await ActorImpactService(self.db).build_assessment(inquiry.case_id)
            artifacts["actor_impact"] = actor_impact

        fc = artifacts.get("financial_crossover")
        if not fc:
            fc = await InquiryFinancialService(self.db).run(
                inquiry.case_id,
                question=inquiry.question,
                financial_text=inquiry.financial_text or "",
                source="inquiry",
            )
            artifacts["financial_crossover"] = fc

        if not artifacts.get("policy_industry"):
            artifacts["policy_industry"] = await PolicyIndustryService(self.db).build_map(
                inquiry.case_id, premise=inquiry.question
            )

        if not artifacts.get("morph_bootstrap"):
            parsed = inquiry.parsed_trigger or {}
            artifacts["morph_bootstrap"] = MorphBootstrapService().bootstrap(
                question=inquiry.question,
                event_type=parsed.get("event_type", "geopolitical"),
                actors=parsed.get("actors"),
            )

        if not artifacts.get("monitor_suggestions"):
            parsed = inquiry.parsed_trigger or {}
            artifacts["monitor_suggestions"] = InquiryMonitorService().suggest(
                question=inquiry.question,
                parsed_trigger=parsed,
                morph_bootstrap=artifacts.get("morph_bootstrap"),
            )

        smic_result = await self._smic_for_case(inquiry.case_id) if godet_ready else None

        answer = ProspectiveSynthesisService().synthesize(
            question=inquiry.question,
            parsed_trigger=inquiry.parsed_trigger or {},
            actor_impact=actor_impact,
            scenarios=scenario_rows,
            financial_crossover=fc,
            policy_industry=artifacts.get("policy_industry"),
            morph_bootstrap=artifacts.get("morph_bootstrap"),
            monitor_suggestions=artifacts.get("monitor_suggestions"),
            smic_result=smic_result,
            scope_audit=inquiry.scope_audit,
            godet_ready=godet_ready,
        )
        inquiry.answer = answer
        inquiry.status = "completed"
        inquiry.completed_at = datetime.now(timezone.utc)
        prev_answer = None
        history = artifacts.get("answer_history") or []
        if history:
            prev_answer = history[-1].get("answer")
        artifacts["answer_diff"] = compare_inquiry_answers(prev_answer, answer)
        audit = self._audit(artifacts)
        audit.log_event("synthesis_completed", {"probability_pct": answer.get("probability_pct"), "manual": True})
        artifacts["audit_trail"] = audit.trail()
        inquiry.artifacts = artifacts
        await self._schedule_next_if_enabled(inquiry)
        await self.db.commit()
        return {
            "found": True,
            "inquiry_id": inquiry.id,
            "answer": answer,
            "godet_ready": godet_ready,
            "answer_diff": artifacts.get("answer_diff"),
        }

    async def compare_for_case(
        self,
        case_id: int,
        *,
        inquiry_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        r = await self.db.execute(
            select(ProspectiveInquiry)
            .where(ProspectiveInquiry.case_id == case_id)
            .order_by(ProspectiveInquiry.created_at.asc())
        )
        rows = list(r.scalars().all())
        if inquiry_ids:
            allowed = set(inquiry_ids)
            rows = [row for row in rows if row.id in allowed]
        comparison = build_case_inquiry_comparison(rows)
        return {"found": True, "case_id": case_id, **comparison}

    async def wizard_link(self, inquiry_id: int) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"found": False, "error": "Inquiry no trobada"}
        artifacts = inquiry.artifacts or {}
        project_id = artifacts.get("wizard_project_id")
        if not project_id:
            morph = artifacts.get("morph_bootstrap")
            if not morph:
                parsed = inquiry.parsed_trigger or {}
                morph = MorphBootstrapService().bootstrap(
                    question=inquiry.question,
                    event_type=parsed.get("event_type", "geopolitical"),
                    actors=parsed.get("actors"),
                )
            bridge = await InquiryWizardBridgeService(self.db).apply_morph_bootstrap(
                case_id=inquiry.case_id,
                question=inquiry.question,
                morph_bootstrap=morph,
            )
            if bridge.get("ok"):
                project_id = bridge.get("project_id")
                artifacts = self._artifacts(inquiry)
                artifacts["wizard_project_id"] = project_id
                inquiry.artifacts = artifacts
                await self.db.commit()
        return {
            "found": True,
            "inquiry_id": inquiry.id,
            "case_id": inquiry.case_id,
            "project_id": project_id,
            "wizard_paths": {
                "morph": f"/prospective/morph?project={project_id}&inquiry={inquiry.id}",
                "micmac": f"/prospective/micmac?project={project_id}&inquiry={inquiry.id}",
                "scenarios": f"/prospective-analysis?project={project_id}&inquiry={inquiry.id}",
            },
        }

    async def list_for_case(self, case_id: int) -> list[dict[str, Any]]:
        r = await self.db.execute(
            select(ProspectiveInquiry)
            .where(ProspectiveInquiry.case_id == case_id)
            .order_by(ProspectiveInquiry.created_at.desc())
        )
        return [
            {
                "id": row.id,
                "question": row.question,
                "mode": row.mode,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "has_answer": bool(row.answer),
                "auto_rerun_enabled": bool(row.auto_rerun_enabled),
                "next_rerun_at": row.next_rerun_at.isoformat() if row.next_rerun_at else None,
                "run_count": row.run_count or 0,
                "wizard_project_id": (row.artifacts or {}).get("wizard_project_id"),
                "probability_pct": (row.answer or {}).get("probability_pct") if isinstance(row.answer, dict) else None,
            }
            for row in r.scalars().all()
        ]

    async def get_detail(self, inquiry_id: int) -> dict[str, Any]:
        inquiry = await self._get_inquiry(inquiry_id)
        if not inquiry:
            return {"found": False}
        return {
            "found": True,
            "id": inquiry.id,
            "case_id": inquiry.case_id,
            "question": inquiry.question,
            "mode": inquiry.mode,
            "status": inquiry.status,
            "parsed_trigger": inquiry.parsed_trigger,
            "inquiry_scope": inquiry.inquiry_scope,
            "scope_audit": inquiry.scope_audit,
            "steps_log": inquiry.steps_log,
            "artifacts": inquiry.artifacts,
            "answer": inquiry.answer,
            "error_message": inquiry.error_message,
            "auto_rerun_enabled": bool(inquiry.auto_rerun_enabled),
            "rerun_interval_hours": inquiry.rerun_interval_hours,
            "next_rerun_at": inquiry.next_rerun_at.isoformat() if inquiry.next_rerun_at else None,
            "last_rerun_at": inquiry.last_rerun_at.isoformat() if inquiry.last_rerun_at else None,
            "run_count": inquiry.run_count or 0,
            "audit_trail": (inquiry.artifacts or {}).get("audit_trail"),
            "answer_diff": (inquiry.artifacts or {}).get("answer_diff"),
            "answer_history": (inquiry.artifacts or {}).get("answer_history"),
        }
