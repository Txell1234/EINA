"""Unit tests for OSINT data flattening utilities."""
from services.osint_data_utils import (
    extract_search_keywords,
    flatten_osint_items,
    osint_has_error,
    text_from_osint_item,
)


def test_flatten_newsapi_articles():
    data = {
        "status": "ok",
        "articles": [
            {
                "title": "Japan rearmament debate",
                "url": "https://example.com/a",
                "publishedAt": "2025-01-01",
                "description": "Summary text",
            }
        ],
    }
    items = flatten_osint_items(data)
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com/a"
    assert items[0]["title"] == "Japan rearmament debate"


def test_flatten_rss_all_nested():
    data = {
        "status": "success",
        "total": 2,
        "sources": {
            "cfr": {
                "status": "success",
                "items": [
                    {"title": "CFR Article", "url": "https://cfr.org/1", "date": "2025-02-01"},
                ],
            },
            "rand": {
                "status": "error",
                "items": [],
            },
        },
    }
    items = flatten_osint_items(data)
    assert len(items) == 1
    assert items[0]["source"] == "cfr"


def test_flatten_gdelt():
    data = {
        "status": "success",
        "articles": [
            {"title": "Event", "url": "https://news.com/e", "date": "20250101120000"},
        ],
    }
    items = flatten_osint_items(data)
    assert len(items) == 1
    assert items[0]["url"] == "https://news.com/e"


def test_osint_has_error():
    assert osint_has_error({"status": "error", "error": "fail"})
    assert not osint_has_error({"status": "success", "articles": []})


def test_extract_search_keywords_long_briefing():
    brief = (
        "FOCULAITZACIÓ EN REARMAMENT de japó I TOTS els factors: "
        "analisis geopolitic de la trobada diplomatica Trump amb Xi Jinping"
    )
    kw = extract_search_keywords(brief, "Rearmament Japó")
    assert len(kw.split()) <= 10
    lower = kw.lower()
    assert "japan" in lower
    assert "rearmament" in lower or "geopolitical" in lower or "geoeconomic" in lower
    assert "1947" not in kw
    assert "000" not in kw


def test_build_osint_search_queries():
    from services.osint_data_utils import build_osint_search_queries, build_primary_osint_query

    primary = build_primary_osint_query(
        "Rearmament Japó",
        "FOCULAITZACIÓ EN REARMAMENT de japó: analisi geopolítica Trump Xi Indo-Pacific",
    )
    assert "Japan" in primary
    assert "rearmament" in primary.lower()
    assert primary.count(" ") < 8

    qs = build_osint_search_queries(
        "Rearmament Japó",
        "FOCULAITZACIÓ EN REARMAMENT de japó: analisi geopolítica Trump Xi Indo-Pacific",
    )
    assert qs[0] == primary
    assert "United States" not in primary or "Japan" in primary


def test_text_from_osint_item():
    text = text_from_osint_item({"title": "T", "summary": "Body content here"})
    assert "T" in text
    assert "Body" in text
