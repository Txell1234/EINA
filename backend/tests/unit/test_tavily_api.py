"""Unit tests for Tavily API normalization."""
from integrations.tavily_api import TavilyAPIService
from services.osint_data_utils import flatten_osint_items


def test_flatten_tavily_articles():
    data = {
        "status": "success",
        "count": 2,
        "articles": [
            {"title": "A", "url": "https://a.com/1", "summary": "s1", "source": "tavily"},
            {"title": "B", "url": "https://b.com/2", "body": "full body", "source": "tavily"},
        ],
    }
    items = flatten_osint_items(data)
    assert len(items) == 2
    assert items[0]["url"] == "https://a.com/1"


def test_tavily_not_configured():
    svc = TavilyAPIService()
    assert isinstance(svc.configured(), bool)


def test_map_results_to_articles():
    articles = TavilyAPIService._articles_from_map_results(
        ["https://docs.tavily.com/welcome", "docs.tavily.com/api"]
    )
    assert len(articles) == 2
    assert articles[0]["url"].startswith("https://")


def test_crawl_results_to_articles():
    articles = TavilyAPIService._articles_from_crawl_results(
        [
            {"url": "https://x.com/a", "raw_content": "body text", "title": "A"},
        ]
    )
    assert len(articles) == 1
    assert articles[0]["body"] == "body text"


def test_research_sources_to_articles():
    articles = TavilyAPIService._articles_from_research_sources(
        [{"title": "Report", "url": "https://example.com/r"}]
    )
    assert len(articles) == 1
    assert articles[0]["source"] == "tavily_research"
