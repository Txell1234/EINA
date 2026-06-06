"""Tests for prospective inquiry orchestrator."""
import pytest

from services.inquiry_orchestrator_service import InquiryOrchestratorService
from services.parse_trigger_service import ParseTriggerService


@pytest.mark.unit
async def test_create_inquiry(db_session, sample_case):
    svc = InquiryOrchestratorService(db_session)
    row = await svc.create_inquiry(
        sample_case.id,
        "Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
    )
    assert row.id > 0
    assert row.status == "pending"
    assert row.parsed_trigger.get("ok") is True
    assert len(row.inquiry_scope.get("required_terms", [])) >= 2


@pytest.mark.unit
async def test_list_inquiries(db_session, sample_case):
    svc = InquiryOrchestratorService(db_session)
    await svc.create_inquiry(
        sample_case.id,
        "Israel and Indonesia normalize relations by 2027?",
        mode="full",
    )
    items = await svc.list_for_case(sample_case.id)
    assert len(items) == 1
    assert items[0]["status"] == "pending"


@pytest.mark.unit
def test_synthesis_deterministic():
    from services.prospective_synthesis_service import ProspectiveSynthesisService

    parsed = ParseTriggerService().parse(
        "Iran leadership change by 2026?"
    )
    answer = ProspectiveSynthesisService().synthesize(
        question="Iran leadership change by 2026?",
        parsed_trigger=parsed,
        actor_impact={"osint_signals": {"hostile_statements": 2, "cooperative_statements": 1}},
        scenarios=[{"name": "Tensió", "estimated_probability_pct": 45, "possibility": "PLAUSIBLE"}],
        godet_ready=True,
    )
    assert answer["llm_used_in_conclusions"] is False
    assert answer["probability_pct"] == 45.0
    assert len(answer["reasoning"]) >= 1


@pytest.mark.unit
def test_synthesis_with_policy_and_morph():
    from services.prospective_synthesis_service import ProspectiveSynthesisService

    answer = ProspectiveSynthesisService().synthesize(
        question="Hormuz blockade lifted?",
        parsed_trigger={"actors": ["US"], "required_terms": ["hormuz"]},
        policy_industry={"companies": [{"name": "Acme Energy"}]},
        morph_bootstrap={"valid_combinations_count": 12, "godet_preview": [{"name": "Tensió", "possibility": "PLAUSIBLE"}]},
        financial_crossover={"mode": "lite", "crossover": {"final_numbers": {"blended_return_index": 65}}},
        godet_ready=False,
    )
    assert answer["policy_companies_count"] == 1
    assert answer["morph_valid_combinations"] == 12
    assert answer["financial_mode"] == "lite"
    assert any("Policy×Indústria" in r["conclusion"] for r in answer["reasoning"])


@pytest.mark.unit
async def test_compare_for_case(db_session, sample_case):
    from datetime import datetime, timedelta
    from models.prospective_inquiry import ProspectiveInquiry

    t0 = datetime(2026, 1, 1)
    t1 = t0 + timedelta(hours=6)
    q1 = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
        status="completed",
        answer={"probability_pct": 28, "possibility": "PLAUSIBLE"},
        created_at=t0,
    )
    q2 = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Israel and Indonesia normalize relations by 2027?",
        mode="full",
        status="completed",
        answer={"probability_pct": 41, "possibility": "LIKELY"},
        artifacts={"wizard_project_id": 99},
        created_at=t1,
    )
    db_session.add_all([q1, q2])
    await db_session.commit()

    svc = InquiryOrchestratorService(db_session)
    result = await svc.compare_for_case(sample_case.id)
    assert result["found"] is True
    assert result["count"] == 2
    assert result["items"][-1]["diff_vs_previous"]["probability_delta"] == 13.0

    filtered = await svc.compare_for_case(sample_case.id, inquiry_ids=[q2.id])
    assert filtered["count"] == 1
    assert filtered["items"][0]["id"] == q2.id


@pytest.mark.unit
async def test_wizard_link_uses_existing_project(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry

    inquiry = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
        status="completed",
        parsed_trigger={"ok": True, "event_type": "security_maritime"},
        artifacts={"wizard_project_id": 42},
    )
    db_session.add(inquiry)
    await db_session.commit()
    await db_session.refresh(inquiry)

    link = await InquiryOrchestratorService(db_session).wizard_link(inquiry.id)
    assert link["found"] is True
    assert link["project_id"] == 42
    assert f"project=42" in link["wizard_paths"]["morph"]
    assert f"inquiry={inquiry.id}" in link["wizard_paths"]["morph"]


@pytest.mark.unit
async def test_wizard_link_creates_project_when_missing(db_session, sample_case):
    from services.morph_bootstrap_service import MorphBootstrapService
    from models.prospective_inquiry import ProspectiveInquiry

    morph = MorphBootstrapService().bootstrap(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        event_type="security_maritime",
    )
    inquiry = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
        status="completed",
        parsed_trigger={"ok": True, "event_type": "security_maritime"},
        artifacts={"morph_bootstrap": morph},
    )
    db_session.add(inquiry)
    await db_session.commit()
    await db_session.refresh(inquiry)

    link = await InquiryOrchestratorService(db_session).wizard_link(inquiry.id)
    assert link["found"] is True
    assert link["project_id"] > 0
    assert f"inquiry={inquiry.id}" in link["wizard_paths"]["morph"]

