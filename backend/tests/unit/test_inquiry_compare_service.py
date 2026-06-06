"""Tests for inquiry answer comparison."""
import pytest

from services.inquiry_compare_service import compare_inquiry_answers


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
