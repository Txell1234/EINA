"""Parse analytical question into structured trigger (hybrid LLM + rule-based)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from services.inquiry_scope import InquiryScopeProfile, build_inquiry_scope

logger = logging.getLogger(__name__)

EventType = Literal["diplomatic", "military", "economic", "maritime", "energy", "other"]
CONFIDENCE_THRESHOLD = 0.75
MIN_KEYWORD_OVERLAP = 0.4
MAX_RETRIES = 2


class LlmParsePayload(BaseModel):
    """Structured LLM output — validated before merge with rule-based scope."""

    actors: list[str] = Field(..., min_length=1)
    regions: list[str] = Field(..., min_length=1)
    event_type: EventType = "other"
    horizon: str | None = None
    keywords: list[str] = Field(..., min_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_question: str = ""

    @field_validator("actors")
    @classmethod
    def normalize_actors(cls, value: list[str]) -> list[str]:
        out = [a.strip() for a in value if a and a.strip()]
        if not out:
            raise ValueError("Almenys un actor és obligatori")
        return [a[:120] for a in out]

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str]) -> list[str]:
        out = [r.strip() for r in value if r and r.strip()]
        if not out:
            raise ValueError("Almenys una regió és obligatòria")
        return [r[:120] for r in out]


def _clean_json(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _semantic_overlap_check(question: str, keywords: list[str]) -> bool:
    if not keywords:
        return False
    q_lower = question.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in q_lower)
    return (matches / len(keywords)) >= MIN_KEYWORD_OVERLAP


def _merge_llm_with_scope(
    question: str,
    llm: LlmParsePayload,
    scope: InquiryScopeProfile,
) -> dict[str, Any]:
    actors = list(dict.fromkeys([*llm.actors, *scope.actors]))
    geo_focus = list(dict.fromkeys([*llm.regions, *scope.geo_focus]))
    event_type = llm.event_type if llm.confidence >= settings.Q2FS_PARSE_CONFIDENCE_THRESHOLD else scope.event_type
    required_terms = list(dict.fromkeys([*llm.keywords, *scope.required_terms]))[:20]

    return {
        "ok": True,
        "question": question,
        "hypothesis": question,
        "actors": actors[:12],
        "geo_focus": geo_focus[:8],
        "event_type": event_type,
        "horizon_label": llm.horizon or scope.horizon_label,
        "horizon_end": scope.horizon_end,
        "required_terms": required_terms,
        "min_required_matches": scope.min_required_matches,
        "negative_terms": scope.negative_terms[:10],
        "osint_queries": scope.osint_queries,
        "scope": scope.to_dict(),
        "methodology": "hybrid_llm_rule_parse",
        "llm_used": True,
        "parse_confidence": round(llm.confidence, 3),
        "guardrail_violations": [],
    }


class ParseTriggerService:
    """Extract actors, scope, horizon and OSINT queries from a trigger question."""

    def parse(
        self,
        question: str,
        *,
        case_name: str = "",
        case_description: str = "",
    ) -> dict[str, Any]:
        """Synchronous rule-based parse (backward compatible)."""
        return self._parse_rule_based(
            question,
            case_name=case_name,
            case_description=case_description,
        )

    async def parse_hybrid(
        self,
        question: str,
        *,
        case_name: str = "",
        case_description: str = "",
        use_llm: bool | None = None,
    ) -> dict[str, Any]:
        from observability.metrics import (
            LLM_PARSE_CONFIDENCE,
            LLM_PARSE_DURATION_SECONDS,
            LLM_PARSE_LOW_CONFIDENCE_TOTAL,
            LLM_TOKENS_USED_TOTAL,
            PARSE_FALLBACK_TOTAL,
            Q2FS_ERRORS_TOTAL,
        )
        from observability.tracing import q2fs_span

        q = (question or "").strip()
        if len(q) < 15:
            return {"ok": False, "error": "La pregunta ha de tenir almenys 15 caràcters"}

        audit_id = f"parse_{int(time.time() * 1000)}"
        use_llm_flag = settings.Q2FS_PARSE_USE_LLM if use_llm is None else use_llm
        start = time.perf_counter()

        with q2fs_span(
            "parse_trigger",
            "parse_trigger",
            {"question_length": len(q), "use_llm": use_llm_flag, "parse_audit_id": audit_id},
        ) as span:
            scope = build_inquiry_scope(q, case_name=case_name, case_description=case_description)

            from services.llm_service import resolve_provider

            if use_llm_flag and resolve_provider():
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        llm_raw, tokens = await self._call_llm_structured(q)
                        validated = LlmParsePayload.model_validate({**llm_raw, "raw_question": q})
                        violations: list[str] = []

                        if not _semantic_overlap_check(q, validated.keywords):
                            violations.append("low_keyword_overlap")
                            validated = validated.model_copy(update={"confidence": validated.confidence * 0.85})

                        if validated.confidence < settings.Q2FS_PARSE_CONFIDENCE_THRESHOLD:
                            violations.append("low_confidence")
                            LLM_PARSE_LOW_CONFIDENCE_TOTAL.inc()
                            PARSE_FALLBACK_TOTAL.labels(reason="low_confidence").inc()
                            result = self._parse_rule_based(
                                q,
                                case_name=case_name,
                                case_description=case_description,
                                audit_id=audit_id,
                                fallback_reason="low_confidence",
                            )
                            result["guardrail_violations"] = violations + ["llm_fallback_used"]
                            duration = time.perf_counter() - start
                            LLM_PARSE_DURATION_SECONDS.labels(llm_used="false").observe(duration)
                            if span:
                                span.set_attribute("parse.llm_used", False)
                                span.set_attribute("parse.confidence", result.get("parse_confidence", 0))
                            return result

                        merged = _merge_llm_with_scope(q, validated, scope)
                        merged["parse_audit_id"] = audit_id
                        merged["guardrail_violations"] = violations
                        merged["llm_tokens_estimated"] = tokens

                        duration = time.perf_counter() - start
                        if duration > settings.Q2FS_PARSE_TIMEOUT_SECONDS:
                            violations.append("latency_guard")
                            merged["guardrail_violations"] = violations

                        LLM_PARSE_DURATION_SECONDS.labels(llm_used="true").observe(duration)
                        LLM_PARSE_CONFIDENCE.set(merged["parse_confidence"])
                        LLM_TOKENS_USED_TOTAL.labels(operation="parse_trigger").inc(tokens)

                        if span:
                            span.set_attribute("parse.llm_used", True)
                            span.set_attribute("parse.confidence", merged["parse_confidence"])
                            if violations:
                                span.set_attribute("parse.guardrail_violations", ",".join(violations))

                        logger.info(
                            "Parse hybrid OK confidence=%.2f audit=%s",
                            merged["parse_confidence"],
                            audit_id,
                            extra={"parse_confidence": merged["parse_confidence"], "llm_used": True},
                        )
                        return merged

                    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                        logger.warning("LLM parse attempt %d failed: %s", attempt + 1, exc)
                        if attempt >= MAX_RETRIES:
                            break
                        await asyncio.sleep(0.4 * (2**attempt))
                    except Exception as exc:
                        Q2FS_ERRORS_TOTAL.labels(phase="parse_trigger", error_type=type(exc).__name__).inc()
                        logger.warning("LLM parse error → fallback: %s", exc)
                        break

                PARSE_FALLBACK_TOTAL.labels(reason="llm_error").inc()

            result = self._parse_rule_based(
                q,
                case_name=case_name,
                case_description=case_description,
                audit_id=audit_id,
                fallback_reason="llm_unavailable_or_failed" if use_llm_flag else None,
            )
            duration = time.perf_counter() - start
            LLM_PARSE_DURATION_SECONDS.labels(llm_used="false").observe(duration)
            LLM_PARSE_CONFIDENCE.set(result.get("parse_confidence", 0.82))
            if span:
                span.set_attribute("parse.llm_used", False)
                span.set_attribute("parse.confidence", result.get("parse_confidence", 0))
            return result

    def _parse_rule_based(
        self,
        question: str,
        *,
        case_name: str = "",
        case_description: str = "",
        audit_id: str | None = None,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        q = (question or "").strip()
        if len(q) < 15:
            return {"ok": False, "error": "La pregunta ha de tenir almenys 15 caràcters"}

        scope = build_inquiry_scope(q, case_name=case_name, case_description=case_description)
        confidence = 0.82 if scope.actors else 0.65
        violations: list[str] = []
        if fallback_reason:
            violations.append("llm_fallback_used")

        result = {
            "ok": True,
            "question": q,
            "hypothesis": q,
            "actors": scope.actors,
            "geo_focus": scope.geo_focus,
            "event_type": scope.event_type,
            "horizon_label": scope.horizon_label,
            "horizon_end": scope.horizon_end,
            "required_terms": scope.required_terms,
            "min_required_matches": scope.min_required_matches,
            "negative_terms": scope.negative_terms[:10],
            "osint_queries": scope.osint_queries,
            "scope": scope.to_dict(),
            "methodology": "rule_based_parse",
            "llm_used": False,
            "parse_confidence": confidence,
            "guardrail_violations": violations,
            "parse_audit_id": audit_id or f"parse_{int(time.time() * 1000)}",
            "parse_audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if confidence < 0.6:
            return {"ok": False, "error": "ParseTrigger fallit: pregunta massa ambigua"}

        return result

    async def _call_llm_structured(self, question: str) -> tuple[dict[str, Any], int]:
        from services.llm_service import LLMService

        llm = LLMService(mode="extract")
        if not llm.configured:
            raise RuntimeError("LLM no configurat")

        system = (
            "Ets un analista OSINT. Parseja preguntes prospectives en JSON estricte. "
            "NO facis prediccions ni conclusions. "
            "Claus: actors (array), regions (array), event_type (diplomatic|military|economic|"
            "maritime|energy|other), horizon (string|null), keywords (array min 3), "
            "confidence (0-1, la teva confiança en l'extracció)."
        )
        user = f"Pregunta:\n{question}\n\nRetorna NOMÉS JSON vàlid."

        raw = await asyncio.wait_for(
            llm.acomplete(user, system_prompt=system, max_tokens=settings.Q2FS_PARSE_MAX_TOKENS),
            timeout=settings.Q2FS_PARSE_TIMEOUT_SECONDS,
        )
        tokens = _estimate_tokens(raw) + _estimate_tokens(question)
        if tokens > settings.Q2FS_PARSE_MAX_TOKENS:
            raise ValueError("Token guard exceeded")

        data = json.loads(_clean_json(raw))
        return data, tokens

    def build_scope_profile(
        self,
        question: str,
        *,
        case_name: str = "",
        case_description: str = "",
    ) -> InquiryScopeProfile:
        return build_inquiry_scope(
            question,
            case_name=case_name,
            case_description=case_description,
        )
