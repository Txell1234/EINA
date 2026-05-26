"""Tests for extraction coverage metrics."""
from services.extraction_coverage_service import _article_stats


def test_article_stats_pending_extraction():
    articles = [
        {"url": "https://a.com/1", "title": "A", "summary": "short", "query_type": "gdelt"},
        {"url": "https://b.com/2", "title": "B", "summary": "x" * 250, "query_type": "rss"},
    ]
    stats = _article_stats(articles, extracted_urls={"https://b.com/2"})
    assert stats["articles_total"] == 2
    assert stats["extracted_urls"] == 1
    assert stats["pending_extraction"] == 1
    assert stats["needs_enrichment"] == 1
