"""Unit tests for RSS feed fetching and fallbacks."""
import pytest

from integrations.rss_feeds import RSSFeedsService


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Test</title>
<item><title>Article One</title><link>https://example.com/1</link>
<description>Summary one</description><pubDate>Mon, 01 Jan 2025 00:00:00 GMT</pubDate></item>
</channel></rss>"""


@pytest.mark.unit
def test_parse_feed_entries_accepts_valid_xml():
    svc = RSSFeedsService()
    items = svc._parse_feed_entries(SAMPLE_RSS, "https://example.com/feed", "cfr", "geopolitics", 5)
    assert len(items) == 1
    assert items[0]["title"] == "Article One"
    assert items[0]["url"] == "https://example.com/1"


@pytest.mark.unit
def test_parse_feed_entries_rejects_empty():
    svc = RSSFeedsService()
    with pytest.raises(ValueError, match="Feed invàlid o buit"):
        svc._parse_feed_entries("<html><body>not rss</body></html>", "https://x/feed", "brookings", "policy", 5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_feed_cfr_uses_working_url(monkeypatch):
    svc = RSSFeedsService()
    calls: list[str] = []

    async def fake_fetch(url: str) -> str:
        calls.append(url)
        if url == "https://www.cfr.org/feed":
            return SAMPLE_RSS
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(svc, "_fetch_url", fake_fetch)
    result = await svc.fetch_feed("cfr", max_items=5)
    assert result["status"] == "success"
    assert result["feed_url"] == "https://www.cfr.org/feed"
    assert result["feed_via"] == "direct"
    assert result["count"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_feed_falls_back_to_google_news(monkeypatch):
    svc = RSSFeedsService()
    calls: list[str] = []

    async def fake_fetch(url: str) -> str:
        calls.append(url)
        if "news.google.com" in url:
            return SAMPLE_RSS.replace("https://example.com/1", "https://news.google.com/rss/articles/abc")
        from httpx import HTTPStatusError, Request, Response

        req = Request("GET", url)
        resp = Response(403, request=req)
        raise HTTPStatusError("403", request=req, response=resp)

    monkeypatch.setattr(svc, "_fetch_url", fake_fetch)
    result = await svc.fetch_feed("iiss", max_items=5)
    assert result["status"] == "success"
    assert result["feed_via"] == "google_news"
    assert "news.google.com" in result["feed_url"]
    assert len(calls) >= 2
