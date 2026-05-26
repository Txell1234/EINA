"""
Nikkei Asia scraper — HTTP + RSS (no Apify).

Official RSS: https://asia.nikkei.com/rss/feed/nar
Article pages: JSON-LD, Open Graph, HTML fallbacks.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from integrations.nikkei_common import is_nikkei_url, normalize_article

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

NIKKEI_RSS_URLS = (
    "https://asia.nikkei.com/rss/feed/nar",
    "https://asia.nikkei.com/rss/feed/top",
)

MIN_BODY_LEN = 80
_request_lock = asyncio.Lock()
_last_request_at = 0.0


async def _throttle(interval_sec: float) -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < interval_sec:
        await asyncio.sleep(interval_sec - elapsed)
    _last_request_at = time.monotonic()


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(text, "html.parser").get_text(" ")).strip()


def _parse_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            typ = item.get("@type") or ""
            if isinstance(typ, list):
                typ = " ".join(typ)
            if "NewsArticle" in typ or "Article" in typ:
                return item
            graph = item.get("@graph")
            if isinstance(graph, list):
                for node in graph:
                    if isinstance(node, dict):
                        ntyp = str(node.get("@type") or "")
                        if "NewsArticle" in ntyp or "Article" in ntyp:
                            return node
    return {}


def _meta_content(soup: BeautifulSoup, *props: str) -> str:
    for prop in props:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return ""


def parse_article_html(html: str, url: str = "") -> dict[str, Any]:
    """Extract article fields from Nikkei Asia HTML (pure function for tests)."""
    soup = BeautifulSoup(html, "html.parser")
    ld = _parse_json_ld(soup)

    title = (
        str(ld.get("headline") or ld.get("name") or "")
        or _meta_content(soup, "og:title", "twitter:title")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
    ).strip()

    body = ""
    for key in ("articleBody", "description"):
        val = ld.get(key)
        if isinstance(val, str) and len(val) > len(body):
            body = _strip_html(val)
        elif isinstance(val, dict) and val.get("@type") == "Text":
            body = _strip_html(str(val.get("text") or ""))

    if len(body) < MIN_BODY_LEN:
        selectors = (
            "article [data-module='ArticleBody'] p",
            "article .article-body p",
            "[data-module='ArticleBody'] p",
            "article p",
            ".ez-text p",
        )
        for sel in selectors:
            nodes = soup.select(sel)
            if not nodes:
                continue
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in nodes
                if len(p.get_text(strip=True)) > 40
            ]
            candidate = "\n\n".join(paragraphs)
            if len(candidate) > len(body):
                body = candidate
            if len(body) >= MIN_BODY_LEN:
                break

    date = (
        str(ld.get("datePublished") or ld.get("dateModified") or "")
        or _meta_content(soup, "article:published_time", "og:updated_time")
    ).strip()

    authors_raw = ld.get("author")
    authors = ""
    if isinstance(authors_raw, dict):
        authors = str(authors_raw.get("name") or "")
    elif isinstance(authors_raw, list):
        authors = ", ".join(
            str(a.get("name") if isinstance(a, dict) else a) for a in authors_raw if a
        )

    canonical = url
    link_tag = soup.find("link", rel="canonical")
    if link_tag and link_tag.get("href"):
        canonical = str(link_tag["href"]).strip()

    return normalize_article(
        {
            "title": title,
            "url": canonical,
            "body": body,
            "date": date,
            "authors": authors,
        },
        provider="nikkei_own",
    )


def _rss_entries_to_articles(feed: Any, max_items: int) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for entry in feed.entries[:max_items]:
        link = getattr(entry, "link", "") or ""
        if link and not is_nikkei_url(link):
            continue
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        body = _strip_html(summary)
        articles.append(
            normalize_article(
                {
                    "title": getattr(entry, "title", ""),
                    "url": link,
                    "body": body,
                    "date": getattr(entry, "published", "") or getattr(entry, "updated", ""),
                },
                provider="nikkei_own",
            )
        )
    return articles


class NikkeiOwnScraper:
    """Free HTTP/RSS scraper for asia.nikkei.com."""

    def __init__(self, rate_limit_sec: float = 2.0):
        self.rate_limit_sec = max(0.5, float(rate_limit_sec))

    async def _get_html(self, url: str) -> str:
        async with _request_lock:
            await _throttle(self.rate_limit_sec)
            async with httpx.AsyncClient(
                timeout=35.0,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text

    async def scrape_url(self, url: str) -> dict[str, Any] | None:
        if not is_nikkei_url(url):
            return None
        try:
            html = await self._get_html(url)
            article = parse_article_html(html, url)
            if not article.get("title") and not article.get("body"):
                return None
            return article
        except Exception as exc:
            logger.warning("Nikkei scrape failed for %s: %s", url, exc)
            return None

    async def scrape_urls(self, urls: list[str], *, max_items: int = 10) -> dict[str, Any]:
        clean = [u.strip() for u in urls if u and u.strip() and is_nikkei_url(u.strip())]
        if not clean:
            return {
                "status": "error",
                "error": "Cap URL vàlida de asia.nikkei.com",
                "count": 0,
                "articles": [],
            }

        articles: list[dict[str, Any]] = []
        for url in clean[:max_items]:
            item = await self.scrape_url(url)
            if item:
                articles.append(item)

        if not articles:
            return {
                "status": "error",
                "error": "No s'han pogut extreure articles (paywall o HTML canviat)",
                "count": 0,
                "articles": [],
            }

        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "nikkei_own",
            "message": f"{len(articles)} articles Nikkei Asia (scraper propi)",
        }

    async def fetch_latest(self, *, max_items: int = 10) -> dict[str, Any]:
        max_items = max(1, min(int(max_items), 25))
        last_error: str | None = None

        for feed_url in NIKKEI_RSS_URLS:
            try:
                async with _request_lock:
                    await _throttle(self.rate_limit_sec)
                    async with httpx.AsyncClient(
                        timeout=25.0,
                        follow_redirects=True,
                        headers={
                            **DEFAULT_HEADERS,
                            "Accept": "application/rss+xml, application/xml, text/xml, */*",
                        },
                    ) as client:
                        resp = await client.get(feed_url)
                        resp.raise_for_status()
                        text = resp.text

                feed = feedparser.parse(text)
                articles = _rss_entries_to_articles(feed, max_items)

                if articles:
                    enriched: list[dict[str, Any]] = []
                    for art in articles[:max_items]:
                        url = art.get("url") or ""
                        if url and len(art.get("body") or "") < MIN_BODY_LEN:
                            full = await self.scrape_url(url)
                            if full and len(full.get("body") or "") > len(art.get("body") or ""):
                                enriched.append(full)
                            else:
                                enriched.append(art)
                        else:
                            enriched.append(art)

                    return {
                        "status": "success",
                        "count": len(enriched),
                        "articles": enriched,
                        "provider": "nikkei_own",
                        "feed_url": feed_url,
                        "message": f"{len(enriched)} titulars Nikkei Asia via RSS",
                    }
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Nikkei RSS %s failed: %s", feed_url, exc)

        return {
            "status": "error",
            "error": "No s'ha pogut llegir el RSS de Nikkei Asia",
            "message": last_error or "Error desconegut",
            "count": 0,
            "articles": [],
        }
