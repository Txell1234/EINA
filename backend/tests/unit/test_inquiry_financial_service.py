"""Tests for inquiry financial lite layer."""
import pytest

from services.inquiry_financial_service import InquiryFinancialService


@pytest.mark.unit
async def test_inquiry_financial_lite(db_session, sample_case):
    svc = InquiryFinancialService(db_session)
    result = await svc.run(
        sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
    )
    assert result["found"] is True
    assert result["mode"] == "lite"
    assert "crossover" in result
    assert result["crossover"]["llm_used_in_conclusions"] is False
    assert "policy_industry" in result


@pytest.mark.unit
async def test_inquiry_financial_full_with_text(db_session, sample_case):
    svc = InquiryFinancialService(db_session)
    result = await svc.run(
        sample_case.id,
        question="Market outlook for energy sector?",
        financial_text="PRAAMS sample: sector energy, outlook neutral, confidence 72%",
    )
    assert result["found"] is True
    assert "crossover" in result
