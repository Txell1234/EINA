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
