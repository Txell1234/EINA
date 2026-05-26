"""Unit tests for Tavily pipeline helpers."""
from services.tavily_pipeline_service import (
    rank_urls_for_extraction,
    select_crawl_seeds,
)


def test_rank_urls_prefers_geopolitics_domains():
    urls = [
        "https://random-blog.com/post",
        "https://www.reuters.com/world/asia",
        "https://example.org/x",
    ]
    ranked = rank_urls_for_extraction(urls, keywords="asia defense")
    assert "reuters.com" in ranked[0]


def test_select_crawl_seeds_from_text():
    seeds = select_crawl_seeds(
        "Japan defense spending Nikkei analysis",
        "Rearmament in Indo-Pacific",
        max_seeds=2,
    )
    assert len(seeds) >= 1
    assert seeds[0]["url"].startswith("https://")
