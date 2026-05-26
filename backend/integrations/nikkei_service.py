"""
Nikkei Asia facade — own scraper, Apify, or auto (own first, Apify fallback).
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from integrations.apify_nikkei import NikkeiApifyService
from integrations.nikkei_scraper import NikkeiOwnScraper

logger = logging.getLogger(__name__)

MIN_BODY_AUTO_FALLBACK = 200


def _provider_mode() -> str:
    mode = (settings.NIKKEI_PROVIDER or "auto").strip().lower()
    if mode not in ("own", "apify", "auto"):
        return "auto"
    return mode


def _body_len(article: dict[str, Any]) -> int:
    return len(str(article.get("body") or article.get("summary") or "").strip())


class NikkeiService:
    """Unified Nikkei Asia ingestion."""

    def __init__(self) -> None:
        self._own = NikkeiOwnScraper(rate_limit_sec=settings.NIKKEI_RATE_LIMIT_SEC)
        self._apify = NikkeiApifyService()

    @property
    def requires_apify_key(self) -> bool:
        return _provider_mode() == "apify"

    @property
    def can_enrich(self) -> bool:
        mode = _provider_mode()
        if mode == "apify":
            return self._apify.configured
        return True

    async def scrape_urls(self, urls: list[str], *, max_items: int = 10) -> dict[str, Any]:
        mode = _provider_mode()

        if mode == "apify":
            return await self._apify.scrape_urls(urls, max_items=max_items)

        if mode == "own":
            return await self._own.scrape_urls(urls, max_items=max_items)

        # auto: own first, Apify for thin bodies
        own_result = await self._own.scrape_urls(urls, max_items=max_items)
        if own_result.get("status") != "success":
            if self._apify.configured:
                return await self._apify.scrape_urls(urls, max_items=max_items)
            return own_result

        articles = list(own_result.get("articles") or [])
        if not self._apify.configured:
            return own_result

        thin_urls = [
            str(a.get("url") or "")
            for a in articles
            if a.get("url") and _body_len(a) < MIN_BODY_AUTO_FALLBACK
        ]
        if not thin_urls:
            return own_result

        logger.info("Nikkei auto: Apify fallback for %d URLs with short body", len(thin_urls))
        apify_result = await self._apify.scrape_urls(thin_urls, max_items=len(thin_urls))
        if apify_result.get("status") != "success":
            return own_result

        by_url = {str(a.get("url") or ""): a for a in apify_result.get("articles") or []}
        merged: list[dict[str, Any]] = []
        for art in articles:
            url = str(art.get("url") or "")
            alt = by_url.get(url)
            if alt and _body_len(alt) > _body_len(art):
                merged.append({**art, **alt, "enrichment_source": "apify_nikkei"})
            else:
                merged.append(art)

        return {
            **own_result,
            "count": len(merged),
            "articles": merged,
            "message": f"{len(merged)} articles (propi + Apify fallback)",
        }

    async def fetch_latest(self, *, max_items: int = 10) -> dict[str, Any]:
        mode = _provider_mode()

        if mode == "apify":
            return await self._apify.fetch_latest(max_items=max_items)

        own_result = await self._own.fetch_latest(max_items=max_items)

        if mode == "own":
            return own_result

        if own_result.get("status") != "success":
            if self._apify.configured:
                return await self._apify.fetch_latest(max_items=max_items)
            return own_result

        if not self._apify.configured:
            return own_result

        articles = list(own_result.get("articles") or [])
        thin_urls = [
            str(a.get("url") or "")
            for a in articles
            if a.get("url") and _body_len(a) < MIN_BODY_AUTO_FALLBACK
        ]
        if not thin_urls:
            return own_result

        apify_result = await self._apify.scrape_urls(thin_urls, max_items=len(thin_urls))
        if apify_result.get("status") != "success":
            return own_result

        by_url = {str(a.get("url") or ""): a for a in apify_result.get("articles") or []}
        merged = []
        for art in articles:
            url = str(art.get("url") or "")
            alt = by_url.get(url)
            if alt and _body_len(alt) > _body_len(art):
                merged.append({**art, **alt})
            else:
                merged.append(art)
        return {**own_result, "articles": merged, "count": len(merged)}
