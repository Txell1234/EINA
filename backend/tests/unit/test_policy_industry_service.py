"""Tests for policy-industry stakeholder mapping."""
import pytest

from services.policy_industry_profiles import profiles_for_themes, looks_like_company
from services.policy_industry_service import PolicyIndustryService, _score_premise_match


@pytest.mark.unit
def test_profiles_for_rearmament_theme():
    profiles = profiles_for_themes({"rearmament"})
    names = {p["name"] for p in profiles}
    assert "Mitsubishi Heavy Industries" in names
    assert "Lockheed Martin" in names


@pytest.mark.unit
def test_looks_like_company():
    assert looks_like_company("Lockheed Martin")
    assert not looks_like_company("Japan")


@pytest.mark.unit
def test_premise_match_score():
    company = {
        "name": "Mitsubishi Heavy Industries",
        "aliases": ["MHI"],
        "sectors": ["naval"],
        "policy_link": "defense budget Japan",
        "matched_themes": ["rearmament"],
    }
    score = _score_premise_match("Japanese rearmament and naval modernization budget", company)
    assert score >= 2.0


@pytest.mark.unit
async def test_build_map_japan_case(db_session, sample_case):
    sample_case.name = "Rearmament Japó 2030"
    sample_case.description = (
        "Anàlisi del rearmament japonès, pressupost de defensa, JSDF i Indo-Pacífic."
    )
    await db_session.commit()

    result = await PolicyIndustryService(db_session).build_map(sample_case.id)
    assert result["found"] is True
    assert result["summary"]["companies_total"] >= 5
    assert result["summary"]["domestic"] >= 1
    assert result["summary"]["overseas"] >= 1
    assert "rearmament" in result["themes"] or "indo_pacific" in result["themes"]


@pytest.mark.unit
async def test_build_map_with_premise(db_session, sample_case):
    sample_case.description = "Japan defense procurement F-35 contractors"
    await db_session.commit()
    premise = "Quines empreses es beneficien del rearmament japonès i compres F-35?"
    result = await PolicyIndustryService(db_session).build_map(sample_case.id, premise=premise)
    assert result["premise"] == premise
    assert len(result["premise_links"]) >= 1
