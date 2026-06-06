"""Parse analytical question into structured trigger (rule-based, no conclusions)."""
from __future__ import annotations

from typing import Any

from services.inquiry_scope import InquiryScopeProfile, build_inquiry_scope


class ParseTriggerService:
    """Extract actors, scope, horizon and OSINT queries from a trigger question."""

    def parse(
        self,
        question: str,
        *,
        case_name: str = "",
        case_description: str = "",
    ) -> dict[str, Any]:
        q = (question or "").strip()
        if len(q) < 15:
            return {"ok": False, "error": "La pregunta ha de tenir almenys 15 caràcters"}

        scope = build_inquiry_scope(q, case_name=case_name, case_description=case_description)
        return {
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
        }

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
