"""Tests for actor/institution typology and analytical lenses."""
from schemas.actor_typology import (
    build_analytical_profile,
    classify_signal_type,
    infer_institution_subtype,
    normalize_actor_class,
    resolve_analysis_lenses,
)


def test_normalize_actor_class():
    assert normalize_actor_class("country") == "state"
    assert normalize_actor_class("organization") == "institution"
    assert normalize_actor_class("state") == "state"


def test_infer_institution_subtype():
    assert infer_institution_subtype("Japan", "state") == "government"
    assert infer_institution_subtype("NATO", "alliance") == "multilateral_org"
    assert infer_institution_subtype("Brookings Institution", "institution") == "think_tank"
    assert infer_institution_subtype("Mitsubishi Heavy Industries", "company") == "corporate"


def test_resolve_analysis_lenses_geopolitical():
    lenses = resolve_analysis_lenses("geopolitical", {"rearmament", "indo_pacific"})
    assert "public_sector" in lenses
    assert "early_warning" in lenses


def test_resolve_analysis_lenses_business():
    lenses = resolve_analysis_lenses("business", {"market_entry", "regulatory"})
    assert "private_sector" in lenses
    assert "market_entry" in lenses


def test_build_analytical_profile():
    profile = build_analytical_profile(
        case_type="geopolitical",
        themes={"rearmament", "sanctions"},
    )
    assert profile.case_type == "geopolitical"
    assert "rearmament" in profile.theme_labels
    assert profile.institution_subtypes_focus
    assert "defense_agency" in profile.institution_subtypes_focus or "regulator" in profile.institution_subtypes_focus
    assert len(profile.scenario_types) == 4


def test_classify_signal_type():
    assert classify_signal_type(
        "Japan passed a new defense budget law and long-term strategy reform.",
        topic="defense",
    ) == "structural"
    assert classify_signal_type(
        "Leaders met at a summit and issued a joint statement today.",
        topic="diplomacy",
    ) == "episodic"
