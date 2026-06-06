"""Tests for inquiry monitor suggestions."""
import pytest

from services.inquiry_monitor_service import InquiryMonitorService


@pytest.mark.unit
def test_monitor_suggestions_from_question():
    svc = InquiryMonitorService()
    result = svc.suggest(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        parsed_trigger={
            "required_terms": ["hormuz", "blockade", "trump"],
            "actors": ["US", "Iran"],
            "horizon_label": "12m",
        },
        morph_bootstrap={
            "godet_preview": [{"name": "Equilibri", "config": "C1/C2", "possibility": "PLAUSIBLE"}]
        },
    )
    assert result["llm_used"] is False
    assert result["count"] >= 2
    assert len(result["suggested_monitors"]) >= 2
    assert len(result["suggested_milestones"]) >= 1
