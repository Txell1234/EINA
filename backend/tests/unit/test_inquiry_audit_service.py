"""Tests for inquiry audit trail."""
import pytest

from services.inquiry_audit_service import InquiryAuditService


@pytest.mark.unit
def test_audit_trail_run_and_steps():
    audit = InquiryAuditService({})
    run = audit.begin_run()
    assert run == 1
    audit.log_step("osint", ok=True, detail={"kept": 5})
    audit.log_event("synthesis_completed", {"probability_pct": 42})
    trail = audit.trail()
    assert len(trail) == 3
    assert trail[0]["event"] == "run_started"
    assert trail[-1]["event"] == "synthesis_completed"
    assert audit.artifacts["run_number"] == 1
