"""Tests for PRAAMS/InvestWatch-style financial document parsing."""
import pytest

from services.financial_document_service import parse_financial_document


PRAAMS_SAMPLE = """
PRAAMS InvestWatch — Mitsubishi Heavy Industries (7011.T)

Return factors (green sectors):
Growth potential: 6/7
Valuation: 5/7
Momentum: 4/7

Risk factors (red sectors):
Liquidity risk: 3/7
Geopolitical risk: 4/7
Leverage: 2/7

Recommendation: BUY
Probability 62%
"""


@pytest.mark.unit
def test_parse_investwatch_scores():
    parsed = parse_financial_document(PRAAMS_SAMPLE, source="praams")
    assert parsed["parse_status"] == "ok"
    metrics = parsed["metrics"]
    assert len(metrics["return_factors"]) >= 3
    assert len(metrics["risk_factors"]) >= 3
    iw = metrics["investwatch_summary"]
    assert iw["avg_return_score"] is not None
    assert iw["avg_risk_score"] is not None
    assert iw["signal"] == "more_return_than_risk"
    assert "BUY" in metrics["recommendations"]


@pytest.mark.unit
def test_parse_percentages_and_probabilities():
    text = "Risk exposure: 45%\nProbability 62%\nReturn score 78%"
    parsed = parse_financial_document(text)
    metrics = parsed["metrics"]
    assert len(metrics["percentages"]) >= 1
    assert len(metrics["probabilities"]) >= 1


@pytest.mark.unit
def test_empty_text_fails():
    parsed = parse_financial_document("   ")
    assert parsed["parse_status"] == "failed"
