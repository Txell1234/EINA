"""Tests for geographic NER helpers."""
from services.geo_ner import extract_geo_entities
from services.osint_geo_utils import (
    article_provider,
    bump_osint_source_counts,
    osint_provider_from_query_type,
)


def test_extract_geo_entities_region_phrase():
    text = "Tensions rise in the South China Sea between naval forces."
    entities = extract_geo_entities(text)
    labels = {e["label"] for e in entities}
    assert "Mar de la Xina Meridional" in labels


def test_extract_geo_entities_keyword():
    text = "Singapore hosts a regional security summit."
    entities = extract_geo_entities(text)
    labels = {e["label"] for e in entities}
    assert "Singapur" in labels


def test_osint_provider_from_query_type():
    assert osint_provider_from_query_type("tavily_search") == "tavily"
    assert osint_provider_from_query_type("gdelt") == "gdelt"
    assert osint_provider_from_query_type("unknown_x") == "unknown_x"


def test_article_provider_prefers_article_source():
    assert article_provider({"source": "gdelt"}, "tavily") == "gdelt"
    assert article_provider({}, "tavily") == "tavily"


def test_bump_osint_source_counts():
    data = bump_osint_source_counts({"count": 1}, "tavily")
    assert data["osint_sources"]["tavily"] == 1
    assert data["primary_osint_source"] == "tavily"

    merged = bump_osint_source_counts(data, "gdelt", increment=2)
    assert merged["osint_sources"]["gdelt"] == 2
    assert merged["primary_osint_source"] == "gdelt"
