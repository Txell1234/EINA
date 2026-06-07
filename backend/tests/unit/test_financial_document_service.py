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
    text = "Risk exposure: 45%\nProbability 62%\nRevenue climbed 8.5%"
    parsed = parse_financial_document(text)
    metrics = parsed["metrics"]
    assert len(metrics["key_metrics"]) >= 1
    assert any("Revenue" in m["label"] for m in metrics["key_metrics"])
    assert len(metrics["probabilities"]) >= 1


@pytest.mark.unit
def test_news_garbage_percentages_filtered():
    text = (
        "down from 14.9% and into 52.0% suggests volatility. "
        "Profit Jumps 23.0% on strong orders. Recommendation: BUY"
    )
    parsed = parse_financial_document(text)
    metrics = parsed["metrics"]
    labels = " ".join(m["label"] for m in metrics["key_metrics"]).lower()
    assert "down from" not in labels
    assert "into" not in labels
    assert metrics["primary_recommendation"] == "BUY"
    assert metrics["recommendations"] == ["BUY"]


@pytest.mark.unit
def test_primary_recommendation_not_every_sell_in_body():
    text = "Analysts say SELL pressure remains. Recommendation: HOLD\nGrowth: 5/7"
    parsed = parse_financial_document(text, source="praams")
    assert parsed["metrics"]["primary_recommendation"] == "HOLD"


@pytest.mark.unit
def test_detect_kawasaki_in_news_text():
    from services.financial_document_service import detect_companies_in_text

    text = (
        "Kawasaki Heavy Industries shares jumped more than 9% after profit rose 23%. "
        "Recommendation: BUY"
    )
    hits = detect_companies_in_text(text, title="KHI earnings beat")
    assert any("Kawasaki" in h["name"] for h in hits)


@pytest.mark.unit
def test_parse_kawasaki_news_sets_company():
    text = "Kawasaki's profit rising 7.3% on defense orders. Recommendation: HOLD"
    parsed = parse_financial_document(text)
    assert "Kawasaki" in (parsed["metrics"].get("company_name") or "")
    assert len(parsed["metrics"].get("detected_companies") or []) >= 1


@pytest.mark.unit
def test_empty_text_fails():
    parsed = parse_financial_document("   ")
    assert parsed["parse_status"] == "failed"


@pytest.mark.unit
def test_needs_llm_narrative_investwatch_skips_llm():
    from services.financial_document_service import needs_llm_narrative

    parsed = parse_financial_document(PRAAMS_SAMPLE, source="praams")
    need, reason = needs_llm_narrative(PRAAMS_SAMPLE, parsed["metrics"])
    assert need is False
    assert reason == "investwatch_structured"


@pytest.mark.unit
def test_needs_llm_narrative_prose_without_structure():
    from services.financial_document_service import needs_llm_narrative

    text = (
        "The company reported mixed results amid geopolitical tension in the region. "
        "Analysts remain cautious about supply chain exposure and defense budget timing. "
        "Management highlighted submarine orders but gave no explicit rating."
    ) * 3
    parsed = parse_financial_document(text)
    need, reason = needs_llm_narrative(text, parsed["metrics"])
    assert need is True
    assert reason in ("no_company_detected", "unstructured_prose", "prose_without_recommendation")


@pytest.mark.unit
def test_preview_parse_detects_kawasaki_ticker():
    from services.financial_document_service import preview_parse

    text = "Kawasaki Heavy Industries profit rose. Recommendation: HOLD"
    preview = preview_parse(text, source="praams", title="KHI — InvestWatch")
    assert "Kawasaki" in (preview.get("company_name") or "")
    assert preview.get("suggested_ticker") == "7012.T"


@pytest.mark.unit
def test_ticker_for_company_profile():
    from services.policy_industry_profiles import ticker_for_company

    assert ticker_for_company("Kawasaki Heavy Industries") == "7012.T"
    assert ticker_for_company("MHI") == "7011.T"


@pytest.mark.unit
def test_apply_reference_entity_pins_metrics():
    from services.financial_document_service import apply_reference_entity, parse_financial_document

    parsed = parse_financial_document("Revenue up 5%. Recommendation: HOLD")
    metrics = parsed["metrics"]
    apply_reference_entity(metrics, "Kawasaki Heavy Industries", source="user")
    assert metrics["reference_entity"] == "Kawasaki Heavy Industries"
    assert metrics["reference_entity_source"] == "user"
    assert metrics["company_name"] == "Kawasaki Heavy Industries"
    assert metrics["suggested_ticker"] == "7012.T"


KAWASAKI_NEWS_BLOB = """
return metric, like Sharpe ratio, and it tells how much return the
7012.T reported revenue of JPY 2 311 267mn in the last 12 months, up 1% from FY25.
EPS fell 1% from FY25.
return on assets (RoA), amounted to 3.3% in the last year; analysts predict that RoA will be 4.0% in FY26.
return on capital employed (RoCE) declined to 8.1%, above the sector average.
The estimate for FY26 for RoCE is 13.8%.
EBITDA margin amounted to 10.7% in the last year.
requiring 6.2% yearly revenue growth. This yields a fair value estimate of ¥3398, representing a 14% upside to current price.
Nikkei Asia reported Friday. Kawasaki's shares jumped more than 9% in morning trading.
The Nikkei 225 rose 0.52%.
"""


@pytest.mark.unit
def test_kawasaki_news_rejects_garbage_company_and_derives_buy():
    from services.financial_document_service import (
        apply_reference_entity,
        build_report_narrative,
        is_valid_company_name,
        parse_financial_document,
    )

    parsed = parse_financial_document(KAWASAKI_NEWS_BLOB, source="custom", title="kawasaki")
    metrics = parsed["metrics"]
    assert not is_valid_company_name("return metric, like Sharpe ratio, and it tells how much return the")
    apply_reference_entity(
        metrics,
        "Kawasaki Heavy Industries",
        source="user",
        text=KAWASAKI_NEWS_BLOB,
        title="kawasaki",
    )
    assert metrics["company_name"] == "Kawasaki Heavy Industries"
    assert metrics["derived_signal"] == "BUY"
    assert metrics["fair_value_upside_pct"] == 14.0
    labels = {m["label"].lower() for m in metrics["key_metrics"]}
    assert "nikkei" not in labels
    roa_entries = [m for m in metrics["key_metrics"] if (m.get("label") or "").lower() == "roa"]
    if roa_entries:
        assert roa_entries[0].get("metric_kind") == "ratio"
    narrative = build_report_narrative(
        "Kawasaki Heavy Industries",
        title="kawasaki",
        metrics=metrics,
        eina_link={"found": True, "origins": ["policy"], "beneficiary_rationale": "Submarins Sōryū."},
    )
    assert "Kawasaki" in narrative
    assert "Sharpe" not in narrative
    assert "BUY" in narrative or "Senyal inferit" in narrative


@pytest.mark.unit
def test_parse_praams_investwatch_pdf_kawasaki():
    """PRAAMS InvestWatch PDF export (graphical clock; textual factors + verdicts)."""
    from pathlib import Path
    from services.financial_document_service import extract_text_from_bytes, parse_financial_document

    sample = """
Kawasaki Heavy Industries, Ltd.7012.T 4
EquityJapanIndustrials
07.06.2026
Key risks factors
Good trading liquidity
Sufficiently resilient to price shocks
Moderate default risk
Key return factors
Decent dividends
Somewhat favourable analyst view
Poor growth
Valuation: Fairly valued
Performance: Mixed
Analyst view: Somewhat favourable
The average target price of 7012.T is 3791 and suggests 31%
upside potential. Usually, this means a BUY recommendation
among investment firms.
Profitability: Average
return on assets (RoA), amounted to 3.3% in the last 12 months.
Growth: Poor
7012.T reported revenue up 1% from FY25. EPS fell 1% from FY25.
"""
    parsed = parse_financial_document(sample, source="praams", title="InvestWatch 7012.T")
    m = parsed["metrics"]
    assert m["parse_mode"] == "praams_investwatch"
    assert m["praams_ratio"] == 4
    assert m["primary_recommendation"] == "BUY"
    assert m["fair_value_upside_pct"] == 31.0
    assert "Poor growth" in (m.get("key_return_summaries") or [])
    assert m.get("factor_verdicts", {}).get("Growth") == "Poor"
    iw = m["investwatch_summary"]
    assert iw["praams_ratio"] == 4
    assert iw["avg_return_score"] is not None

    pdf = Path(
        r"C:\Users\merit\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm"
        r"\LocalState\sessions\FB9C24C8DCA799FC174CDD838BF82715D90CACAB"
        r"\transfers\2026-23\PRAAMS InvestWatch — 7012.T — 07 Jun 2026 - 17.36.39.pdf"
    )
    if pdf.exists():
        text = extract_text_from_bytes(pdf.read_bytes(), pdf.name)
        live = parse_financial_document(text, source="praams", title=pdf.stem)
        lm = live["metrics"]
        assert lm["parse_mode"] == "praams_investwatch"
        assert lm["praams_ratio"] == 4
        assert lm["primary_recommendation"] == "BUY"
        assert "Kawasaki" in (lm.get("company_name") or "")
        assert lm["fair_value_upside_pct"] == 31.0
        assert not any(k["label"] == "Profit" and k["value_pct"] == 23.0 for k in lm.get("key_metrics") or [])


@pytest.mark.unit
def test_external_return_uses_upside_not_roa():
    from services.financial_crossover_service import FinancialCrossoverService
    from services.financial_document_service import apply_reference_entity, parse_financial_document

    parsed = parse_financial_document(KAWASAKI_NEWS_BLOB, source="custom", title="kawasaki")
    metrics = parsed["metrics"]
    apply_reference_entity(
        metrics,
        "Kawasaki Heavy Industries",
        source="user",
        text=KAWASAKI_NEWS_BLOB,
        title="kawasaki",
    )
    svc = FinancialCrossoverService(None)  # type: ignore[arg-type]
    ext_return, sources = svc._external_implied_return(metrics)
    assert ext_return == 14.0
    assert any(s.get("label") == "Upside valor just" for s in sources)
