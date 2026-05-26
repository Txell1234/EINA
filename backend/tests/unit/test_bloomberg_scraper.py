"""Tests for Bloomberg own scraper."""
from pathlib import Path

import feedparser
import pytest

from integrations.bloomberg_common import is_bloomberg_url
from integrations.bloomberg_scraper import (
    _edition_filter,
    _parse_feed_entry,
    parse_article_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bloomberg_sample.rss"


@pytest.mark.unit
def test_is_bloomberg_url():
    assert is_bloomberg_url("https://www.bloomberg.com/news/articles/2026-05-25/test")
    assert is_bloomberg_url("https://feeds.bloomberg.com/markets/news.rss")
    assert not is_bloomberg_url("https://www.reuters.com/world")


@pytest.mark.unit
def test_parse_feed_entry_asia_filter():
    feed = feedparser.parse(FIXTURE.read_text(encoding="utf-8"))
    asia_filt = _edition_filter("asia")
    assert asia_filt is not None
    articles = []
    for entry in feed.entries:
        art = _parse_feed_entry(entry, section="markets", edition="asia")
        if art and asia_filt(art):
            articles.append(art)
    assert len(articles) == 1
    assert "Japan" in articles[0]["title"]
    assert len(articles[0]["body"]) >= 40


@pytest.mark.unit
def test_parse_feed_entry_us_filter():
    feed = feedparser.parse(FIXTURE.read_text(encoding="utf-8"))
    us_filt = _edition_filter("us")
    articles = []
    for entry in feed.entries:
        art = _parse_feed_entry(entry, section="markets", edition="us")
        if art and us_filt(art):
            articles.append(art)
    assert len(articles) == 1
    assert "Fed" in articles[0]["title"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_latest_global_mock(monkeypatch):
    xml = FIXTURE.read_text(encoding="utf-8")

    async def fake_fetch(self, url: str) -> tuple[int, str]:
        if "feeds.bloomberg.com" in url or "bloomberg.com" in url:
            return 200, xml
        return 404, ""

    monkeypatch.setattr(
        "integrations.bloomberg_scraper.BloombergOwnScraper._fetch_text",
        fake_fetch,
    )

    from integrations.bloomberg_scraper import BloombergOwnScraper

    svc = BloombergOwnScraper(rate_limit_sec=0)
    result = await svc.fetch_latest(edition="global", max_items=5)
    assert result["status"] == "success"
    assert result["count"] >= 2
