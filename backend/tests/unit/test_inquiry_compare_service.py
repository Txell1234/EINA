"""Tests for inquiry answer comparison."""
import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace

from services.inquiry_compare_service import compare_inquiry_answers, build_case_inquiry_comparison


@pytest.mark.unit
def test_compare_probability_delta():
    diff = compare_inquiry_answers(
        {"probability_pct": 30, "possibility": "PLAUSIBLE", "confidence": 50, "reasoning": []},
        {"probability_pct": 42, "possibility": "PLAUSIBLE", "confidence": 58, "reasoning": [{"conclusion": "New"}]},
    )
    assert diff["probability_delta"] == 12.0
    assert diff["possibility_changed"] is False
    assert diff["confidence_delta"] == 8.0
    assert "New" in diff["new_conclusions"]


@pytest.mark.unit
def test_build_case_inquiry_comparison_chronological_delta():
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    t1 = t0 + timedelta(days=1)
    rows = [
        SimpleNamespace(
            id=1,
            question="First trigger question?",
            mode="lite",
            status="completed",
            run_count=1,
            created_at=t0,
            completed_at=t0,
            answer={"probability_pct": 30, "possibility": "PLAUSIBLE", "confidence": 50, "reasoning": []},
            artifacts={"wizard_project_id": 10},
        ),
        SimpleNamespace(
            id=2,
            question="Second trigger question?",
            mode="full",
            status="completed",
            run_count=2,
            created_at=t1,
            completed_at=t1,
            answer={"probability_pct": 45, "possibility": "LIKELY", "confidence": 62, "reasoning": []},
            artifacts={"wizard_project_id": 11},
        ),
    ]
    result = build_case_inquiry_comparison(rows)
    assert result["count"] == 2
    assert result["latest_id"] == 2
    assert len(result["probability_series"]) == 2
    assert result["items"][0]["diff_vs_previous"] is None
    assert result["items"][1]["diff_vs_previous"]["probability_delta"] == 15.0
    assert result["items"][1]["diff_vs_previous"]["possibility_changed"] is True
    assert result["items"][1]["wizard_project_id"] == 11
