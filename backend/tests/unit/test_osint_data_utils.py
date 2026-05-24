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
        "analisis geopolitic de la trobada diplomatica"
    )
    kw = extract_search_keywords(brief, "Rearmament Japó")
    assert len(kw.split()) <= 10
    assert "Japan" in kw or "jap" in kw.lower() or "rearmament" in kw.lower()


def test_text_from_osint_item():
    text = text_from_osint_item({"title": "T", "summary": "Body content here"})
    assert "T" in text
    assert "Body" in text
