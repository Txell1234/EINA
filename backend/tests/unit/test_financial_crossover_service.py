"""Tests for financial report crossover with EINA metrics."""
import pytest

from services.financial_crossover_service import FinancialCrossoverService
from services.financial_document_service import parse_financial_document

PRAAMS_SAMPLE = """
Return factors:
Growth: 6/7
Valuation: 5/7
Risk factors:
Geopolitical: 4/7
Liquidity: 3/7
Recommendation: BUY
"""


@pytest.mark.unit
async def test_ingest_and_crossover(db_session, sample_case):
    svc = FinancialCrossoverService(db_session)
    ingested = await svc.ingest_text(
        sample_case.id,
        PRAAMS_SAMPLE,
        source="praams",
        title="Test PRAAMS",
    )
    assert ingested["report_id"] > 0
    assert ingested["parse_status"] in ("ok", "partial")

    result = await svc.cross_reference(
        sample_case.id,
        report_id=ingested["report_id"],
        external_weight=0.35,
    )
    assert result["found"] is True
    assert "crossover" in result
    cx = result["crossover"]
    assert "final_numbers" in cx
    assert cx.get("llm_used_in_conclusions") is False
    assert isinstance(cx.get("reasoning"), list)
    assert isinstance(cx.get("external_evidence"), list)
    assert len(cx["external_evidence"]) >= 1
    assert isinstance(cx["conclusions"], list)


@pytest.mark.unit
async def test_inline_crossover(db_session, sample_case):
    svc = FinancialCrossoverService(db_session)
    result = await svc.cross_reference(
        sample_case.id,
        inline_text=PRAAMS_SAMPLE,
        source="praams",
    )
    assert result["found"] is True
    nums = result["crossover"]["final_numbers"]
    assert nums.get("external_return_index") is not None


@pytest.mark.unit
async def test_list_reports(db_session, sample_case):
    svc = FinancialCrossoverService(db_session)
    await svc.ingest_text(sample_case.id, PRAAMS_SAMPLE, source="custom")
    reports = await svc.list_reports(sample_case.id)
    assert len(reports) == 1
    assert reports[0]["source"] == "custom"


@pytest.mark.unit
def test_llm_metrics_ignored_in_crossover():
    svc = FinancialCrossoverService(None)  # type: ignore[arg-type]
    parsed = parse_financial_document(PRAAMS_SAMPLE, source="praams")
    metrics = parsed["metrics"]
    metrics["llm_extracted"] = {"risk_scores": [{"score": 99}], "return_scores": [{"score": 99}]}
    external = {"metrics": metrics}
    eina = {"scenarios": [], "investment_recommendations": [], "smic": None, "policy_companies": []}
    out = svc._build_crossover(external, eina)
    assert out["llm_data_ignored"] is True
    assert out["final_numbers"]["external_return_index"] != 99
    assert out["llm_used_in_conclusions"] is False


@pytest.mark.unit
def test_build_crossover_blend():
    svc = FinancialCrossoverService(None)  # type: ignore[arg-type]
    parsed = parse_financial_document(PRAAMS_SAMPLE, source="praams")
    external = {"metrics": parsed["metrics"]}
    eina = {
        "scenarios": [{"probability": 40}, {"probability": 30}],
        "investment_recommendations": [{"confidence_pct": 70, "type": "BUY"}],
        "smic": {"initial_probs": {"a": 0.4, "b": 0.3}},
        "policy_companies": [],
    }
    out = svc._build_crossover(external, eina, external_weight=0.35)
    assert out["final_numbers"]["blended_return_index"] is not None
    assert out["final_numbers"]["eina_scenario_probability_avg"] == 35.0
    assert out["llm_used_in_conclusions"] is False
    assert len(out["external_evidence"]) >= 2
    assert out["final_numbers_explanations"]["blended_return_index"]["because"]
    assert "×" in out["final_numbers_explanations"]["blended_return_index"]["because"]
