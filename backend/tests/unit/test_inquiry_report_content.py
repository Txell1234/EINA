"""Tests for inquiry executive summary export."""
import pytest

from services.inquiry_report_content import build_inquiry_executive_summary


@pytest.mark.unit
def test_build_inquiry_executive_summary_contains_hypothesis():
    detail = {
        "question": "Trump announces US blockade of Hormuz lifted by December 2026?",
        "status": "completed",
        "mode": "lite",
        "answer": {
            "probability_pct": 38,
            "possibility": "possible",
            "conclusions": ["Blocatge parcialment aixecat."],
        },
        "scope_audit": {"queries_run": 2, "kept": 12},
        "artifacts": {
            "morph_bootstrap": {
                "godet_preview": [{"name": "Tensió", "config": "A|B", "possibility": "possible"}],
            },
            "monitor_suggestions": {"suggested_monitors": [{"indicator": "Hormuz traffic"}]},
        },
    }
    html = build_inquiry_executive_summary(detail, lang="ca")
    assert "Resum executiu" in html
    assert "Hormuz" in html
    assert "38" in html
    assert "Blocatge" in html
