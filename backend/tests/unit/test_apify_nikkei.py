"""Tests for Apify Nikkei integration."""
import pytest

from integrations.apify_nikkei import NikkeiApifyService, _normalize_item
from integrations.nikkei_common import is_nikkei_url


@pytest.mark.unit
def test_is_nikkei_url():
    assert is_nikkei_url("https://asia.nikkei.com/Politics/test")
    assert not is_nikkei_url("https://www.reuters.com/world")


@pytest.mark.unit
def test_normalize_item_body():
    item = _normalize_item(
        {
            "title": "Japan boosts defense",
            "url": "https://asia.nikkei.com/Politics/test",
            "articleText": "Full article body here with enough content.",
            "authors": ["Jane Doe"],
            "publishedAt": "2026-05-01",
        }
    )
    assert item["body"].startswith("Full article")
    assert item["authors"] == "Jane Doe"
    assert item["provider"] == "apify_nikkei"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_urls_requires_token():
    svc = NikkeiApifyService(api_token="")
    result = await svc.scrape_urls(["https://asia.nikkei.com/Politics/test"])
    assert result["status"] == "error"
    assert "APIFY" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_urls_rejects_non_nikkei(monkeypatch):
    svc = NikkeiApifyService(api_token="fake-token")
    result = await svc.scrape_urls(["https://example.com/article"])
    assert result["status"] == "error"
    assert "URL" in result["error"]
