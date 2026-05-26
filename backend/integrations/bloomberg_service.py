"""Bloomberg facade — own RSS scraper."""
from __future__ import annotations

from typing import Any

from app.config import settings
from integrations.bloomberg_scraper import BloombergOwnScraper, TOPIC_FEEDS

EDITIONS = sorted(
    {
        "global",
        "asia",
        "europe",
        "us",
        *TOPIC_FEEDS.keys(),
    }
)


class BloombergService:
    def __init__(self) -> None:
        self._own = BloombergOwnScraper(rate_limit_sec=settings.BLOOMBERG_RATE_LIMIT_SEC)

    @staticmethod
    def list_editions() -> list[dict[str, str]]:
        return [
            {"id": "global", "label": "Global (tots els feeds)"},
            {"id": "europe", "label": "Europa (filtre regional)"},
            {"id": "asia", "label": "Àsia / Indo-Pacífic (filtre regional)"},
            {"id": "us", "label": "Estats Units (filtre regional)"},
            {"id": "markets", "label": "Markets"},
            {"id": "politics", "label": "Politics"},
            {"id": "economics", "label": "Economics"},
            {"id": "technology", "label": "Technology"},
            {"id": "industries", "label": "Industries"},
            {"id": "wealth", "label": "Wealth"},
            {"id": "green", "label": "Green"},
            {"id": "opinion", "label": "Opinion"},
            {"id": "crypto", "label": "Crypto"},
            {"id": "businessweek", "label": "Businessweek"},
        ]

    async def fetch_latest(self, *, edition: str = "global", max_items: int = 15) -> dict[str, Any]:
        return await self._own.fetch_latest(edition=edition, max_items=max_items)

    async def scrape_urls(
        self,
        urls: list[str],
        *,
        edition: str = "global",
        max_items: int = 10,
    ) -> dict[str, Any]:
        return await self._own.scrape_urls(urls, max_items=max_items, edition=edition)
