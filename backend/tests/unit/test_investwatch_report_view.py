"""Tests for InvestWatch report view builder."""
import pytest

from services.investwatch_report_view import build_investwatch_report_view


KAWASAKI_PRAAMS_METRICS = {
    "parse_mode": "praams_investwatch",
    "company_name": "Kawasaki Heavy Industries",
    "primary_ticker": "7012.T",
    "praams_ratio": 4,
    "primary_recommendation": "BUY",
    "fair_value_upside_pct": 31.0,
    "key_risk_summaries": [
        "Good trading liquidity",
        "Sufficiently resilient to price shocks",
        "Moderate default risk",
    ],
    "key_return_summaries": [
        "Decent dividends",
        "Somewhat favourable analyst view",
        "Poor growth",
    ],
    "factor_verdicts": {
        "Valuation": "Fairly valued",
        "Growth": "Poor",
        "Analyst view": "Somewhat favourable",
        "Default risk": "Moderate",
    },
    "investwatch_summary": {
        "praams_ratio": 4,
        "avg_return_score": 4.0,
        "avg_risk_score": 4.7,
        "signal": "more_risk_than_return",
    },
    "key_metrics": [
        {"label": "ROA", "value_pct": 3.3, "metric_kind": "ratio"},
        {"label": "Revenue", "value_pct": 1.0, "metric_kind": "growth"},
    ],
}


@pytest.mark.unit
def test_investwatch_report_view_praams_structure():
    out = build_investwatch_report_view(
        KAWASAKI_PRAAMS_METRICS,
        report_context={
            "resolved_company": "Kawasaki Heavy Industries",
            "narrative": "Informe PRAAMS sobre Kawasaki.",
            "eina_link": {
                "found": True,
                "policy_link": "Submarins Indo-Pacífic",
                "beneficiary_rationale": "Constructor Sōryū.",
                "sectors": ["submarines"],
            },
        },
        crossover={
            "tiered_recommendations": {"external_signal": "BUY", "private": [{"action": "ACCUMULATE"}]},
            "final_numbers": {"blended_return_index": 42.5, "external_return_index": 57.1},
        },
        title="InvestWatch 7012.T",
    )
    assert out["layout"] == "eina_investwatch_v1"
    assert out["company"] == "Kawasaki Heavy Industries"
    assert out["ticker"] == "7012.T"
    assert out["praams_ratio"] == 4
    assert out["recommendation"] == "BUY"
    assert out["recommendation_class"] == "positive"
    assert out["has_clock"] is True
    assert len(out["risk_sectors"]) >= 1
    assert len(out["return_sectors"]) >= 3
    assert any(s["label"] == "Growth" for s in out["return_sectors"])
    assert out["eina_overlay"]["linked"] is True
    assert out["eina_overlay"]["private_action"] == "ACCUMULATE"
    assert out["key_metrics"][0]["label"] == "Upside analistes"


@pytest.mark.unit
def test_parse_macro_outlook_asia_2026_pdf():
    from pathlib import Path

    from services.financial_document_service import extract_text_from_bytes
    from services.report_outlook import parse_macro_outlook_text

    pdf = Path(r"C:\Users\merit\Downloads\asia 2026.pdf")
    if not pdf.exists():
        pytest.skip("asia 2026.pdf not on disk")
    text = extract_text_from_bytes(pdf.read_bytes(), pdf.name)
    out = parse_macro_outlook_text(text)
    assert out is not None
    assert out["parse_mode"] == "macro_outlook"
    assert "Asia" in out["title"] or "2026" in out["title"]
    assert len(out["what_to_watch"]) >= 1
    assert len(out["key_risks"]) >= 1
    assert len(out["key_opportunities"]) >= 1
    assert any("RCEP" in s["name"] or "70" in s.get("likelihood_label", "") for s in out["scenarios"])
