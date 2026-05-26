"""Tests for own Nikkei scraper and facade."""
from pathlib import Path

import pytest

from integrations.nikkei_common import is_nikkei_url
from integrations.nikkei_scraper import parse_article_html
from integrations.nikkei_service import NikkeiService

FIXTURE = Path(__file__).parent / "fixtures" / "nikkei_sample.html"


@pytest.mark.unit
def test_is_nikkei_url():
    assert is_nikkei_url("https://asia.nikkei.com/Politics/test")
    assert not is_nikkei_url("https://www.reuters.com/world")


@pytest.mark.unit
def test_parse_article_html_json_ld():
    html = FIXTURE.read_text(encoding="utf-8")
    article = parse_article_html(html, "https://asia.nikkei.com/Politics/test")
    assert "defense spending" in article["title"].lower()
    assert len(article["body"]) >= 80
    assert article["provider"] == "nikkei_own"
    assert "Jane Reporter" in article["authors"]
    assert article["url"] == "https://asia.nikkei.com/Politics/International-relations/Japan-boosts-defense"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_own_scrape_urls(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")

    async def fake_get_html(self, url: str) -> str:
        return html

    monkeypatch.setattr(
        "integrations.nikkei_scraper.NikkeiOwnScraper._get_html",
        fake_get_html,
    )

    from integrations.nikkei_scraper import NikkeiOwnScraper

    svc = NikkeiOwnScraper(rate_limit_sec=0)
    result = await svc.scrape_urls(
        ["https://asia.nikkei.com/Politics/International-relations/Japan-boosts-defense"],
        max_items=1,
    )
    assert result["status"] == "success"
    assert result["count"] == 1
    assert len(result["articles"][0]["body"]) >= 80


@pytest.mark.unit
@pytest.mark.asyncio
async def test_service_auto_uses_own_without_apify(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")

    async def fake_get_html(self, url: str) -> str:
        return html

    monkeypatch.setattr(
        "integrations.nikkei_scraper.NikkeiOwnScraper._get_html",
        fake_get_html,
    )
    monkeypatch.setattr("integrations.nikkei_service.settings.NIKKEI_PROVIDER", "auto")
    monkeypatch.setattr("integrations.nikkei_service.settings.APIFY_API_TOKEN", "")

    svc = NikkeiService()
    result = await svc.scrape_urls(
        ["https://asia.nikkei.com/Politics/International-relations/Japan-boosts-defense"],
        max_items=1,
    )
    assert result["status"] == "success"
    assert result["articles"][0]["provider"] == "nikkei_own"
