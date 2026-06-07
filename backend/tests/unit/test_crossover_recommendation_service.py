"""Tests for tiered crossover recommendations."""
import pytest

from services.crossover_recommendation_service import build_tiered_recommendations
from services.financial_document_service import parse_financial_document

KAWASAKI_PROFILE_CTX = {
    "resolved_company": "Kawasaki Heavy Industries",
    "reference_entity": "Kawasaki Heavy Industries",
    "eina_link": {
        "found": True,
        "name": "Kawasaki Heavy Industries",
        "country": "JP",
        "region": "domestic",
        "roles": ["prime_contractor"],
        "sectors": ["submarines", "aircraft", "transport"],
        "policy_link": "Expansió capacitat submarina Indo-Pacífic",
        "beneficiary_rationale": "Constructor submarins Sōryū/Taigei.",
        "contractor_relationships": [],
    },
}

PRAAMS_HOLD = """
Kawasaki Heavy Industries (7012.T)
Return: Growth 5/7
Risk: Geopolitical 4/7
Recommendation: HOLD
"""


@pytest.mark.unit
def test_tiered_private_and_public():
    metrics = parse_financial_document(PRAAMS_HOLD, source="praams")["metrics"]
    eina = {
        "scenarios": [{"name": "Tensió Crònica", "type": "tension", "probability": 40}],
        "investment_recommendations": [],
        "policy_companies": [],
    }
    out = build_tiered_recommendations(
        metrics,
        eina,
        entity_name="Kawasaki Heavy Industries",
        report_context=KAWASAKI_PROFILE_CTX,
    )
    assert out["focus_entity"] == "Kawasaki Heavy Industries"
    assert out["external_signal"] == "HOLD"
    assert len(out["private"]) >= 1
    assert out["private"][0]["action"] == "HOLD"
    assert out["private"][0]["ticker"] == "7012.T"
    assert out["private"][0].get("justification")
    assert "HOLD" in out["private"][0]["justification"] or "neutre" in out["private"][0]["justification"]
    assert out["private"][0].get("source_label")
    assert len(out["public"]) >= 1
    assert any(r["action"] == "POLICY_ALIGNED" for r in out["public"])
    assert len(out["industries"]) >= 1
    assert any(r["target"] == "Submarines" for r in out["industries"])


@pytest.mark.unit
def test_tiered_satellites_from_contractor_relationships():
    metrics = parse_financial_document("Recommendation: BUY", source="praams")["metrics"]
    ctx = {
        "resolved_company": "Mitsubishi Heavy Industries",
        "eina_link": {
            "found": True,
            "name": "Mitsubishi Heavy Industries",
            "roles": ["prime_contractor"],
            "sectors": ["naval", "missiles"],
            "policy_link": "Pressupost defensa JP",
            "beneficiary_rationale": "Integrador naval JSDF.",
            "contractor_relationships": [
                {"partner": "Lockheed Martin", "type": "license/offset", "region": "overseas"},
            ],
        },
    }
    out = build_tiered_recommendations(
        metrics,
        {"scenarios": [], "investment_recommendations": []},
        entity_name="Mitsubishi Heavy Industries",
        report_context=ctx,
    )
    assert len(out["satellites"]) >= 1
    assert any(s["target"] == "Lockheed Martin" for s in out["satellites"])


@pytest.mark.unit
def test_tiered_kawasaki_news_with_reference_entity():
    from services.financial_document_service import apply_reference_entity, parse_financial_document

    news = (
        "Kawasaki's shares jumped more than 9%. Revenue up 1%. "
        "fair value representing a 14% upside to current price. RoA 3.3%."
    )
    metrics = parse_financial_document(news, source="custom", title="kawasaki")["metrics"]
    apply_reference_entity(
        metrics,
        "Kawasaki Heavy Industries",
        source="user",
        text=news,
        title="kawasaki",
    )
    out = build_tiered_recommendations(
        metrics,
        {"scenarios": [], "investment_recommendations": []},
        entity_name="Kawasaki Heavy Industries",
        report_context=KAWASAKI_PROFILE_CTX,
    )
    assert out["focus_entity"] == "Kawasaki Heavy Industries"
    assert out["external_signal"] == "BUY"
    assert len(out["private"]) >= 1
    assert out["private"][0]["action"] == "ACCUMULATE"
    assert len(out["industries"]) >= 1
    assert len(out["public"]) >= 1


@pytest.mark.unit
def test_tiered_empty_without_entity():
    metrics = {"parse_mode": "partial", "company_name": None}
    out = build_tiered_recommendations(metrics, {}, entity_name=None)
    assert not out["private"]
    assert "Sense entitat" in out["summary"]
