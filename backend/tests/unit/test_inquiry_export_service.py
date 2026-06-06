"""Tests for inquiry HTML export."""
import pytest

from services.inquiry_export_service import build_inquiry_report_html


@pytest.mark.unit
def test_build_inquiry_report_html():
    detail = {
        "question": "Hormuz blockade lifted?",
        "status": "completed",
        "mode": "lite",
        "answer": {
            "probability_pct": 42,
            "possibility": "PLAUSIBLE",
            "possibility_rationale": "Based on OSINT signals.",
            "conclusions": ["Test conclusion"],
        },
        "scope_audit": {"kept": 5, "removed_topic": 2},
        "artifacts": {
            "morph_bootstrap": {
                "godet_preview": [{"name": "Escenari A", "config": "C1/C2", "possibility": "PLAUSIBLE"}]
            }
        },
        "steps_log": [{"step": "parse", "ok": True}],
    }
    html = build_inquiry_report_html(detail)
    assert "Informe prospectiu" in html
    assert "Resum executiu" in html
    assert "Hormuz blockade lifted?" in html
    assert "42" in html
    assert "Escenari A" in html
