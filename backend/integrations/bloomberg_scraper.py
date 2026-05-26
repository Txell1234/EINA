"""
Bloomberg scraper — official RSS (feeds.bloomberg.com) + regional edition filters.

Bloomberg.com HTML often returns 403 for bots; RSS feeds provide headlines,
summaries and partial body text without paywall fetch.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Callable

import feedparser
import httpx
from bs4 import BeautifulSoup

from integrations.bloomberg_common import is_bloomberg_url, normalize_article

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MIN_BODY_LEN = 80
_request_lock = asyncio.Lock()
_last_request_at = 0.0

# Official topic feeds (feeds.bloomberg.com — no bot wall)
TOPIC_FEEDS: dict[str, str] = {
    "markets": "https://feeds.bloomberg.com/markets/news.rss",
    "politics": "https://feeds.bloomberg.com/politics/news.rss",
    "technology": "https://feeds.bloomberg.com/technology/news.rss",
    "economics": "https://feeds.bloomberg.com/economics/news.rss",
    "industries": "https://feeds.bloomberg.com/industries/news.rss",
    "wealth": "https://feeds.bloomberg.com/wealth/news.rss",
    "green": "https://feeds.bloomberg.com/green/news.rss",
    "opinion": "https://feeds.bloomberg.com/bview/news.rss",
    "crypto": "https://feeds.bloomberg.com/crypto/news.rss",
    "businessweek": "https://feeds.bloomberg.com/businessweek/news.rss",
}

GLOBAL_FEED_KEYS = (
    "markets",
    "politics",
    "economics",
    "technology",
    "industries",
    "wealth",
    "green",
    "opinion",
)

_ASIA_MARKERS = (
    "asia",
    "asian",
    "china",
    "chinese",
    "japan",
    "japanese",
    "india",
    "indian",
    "singapore",
    "hong-kong",
    "taiwan",
    "korea",
    "korean",
    "asean",
    "indo-pacific",
    "/jp/",
    "beijing",
    "shanghai",
    "mumbai",
    "sydney",
)

_EUROPE_MARKERS = (
    "europe",
    "european",
    "eu ",
    "eurozone",
    "uk ",
    "u.k.",
    "britain",
    "germany",
    "france",
    "italy",
    "spain",
    "london",
    "paris",
    "berlin",
    "ecb",
    "brexit",
    "/europe/",
)

_US_MARKERS = (
    "u.s.",
    "u.s ",
    "united states",
    "america",
    "american",
    "washington",
    "wall street",
    "fed ",
    "federal reserve",
    "treasury",
    "white house",
    "congress",
    "nasdaq",
    "s&p",
)


def _haystack(article: dict[str, Any]) -> str:
    return " ".join(
        [
            str(article.get("url") or ""),
            str(article.get("title") or ""),
            str(article.get("body") or ""),
            str(article.get("summary") or ""),
        ]
    ).lower()


def _matches_markers(text: str, markers: tuple[str, ...]) -> bool:
    return any(m in text for m in markers)


def _edition_filter(edition: str) -> Callable[[dict[str, Any]], bool] | None:
    key = edition.strip().lower()
    if key in ("global", "all", ""):
        return None
    if key == "asia":
        return lambda a: _matches_markers(_haystack(a), _ASIA_MARKERS)
    if key == "europe":
        return lambda a: _matches_markers(_haystack(a), _EUROPE_MARKERS)
    if key in ("us", "usa", "americas"):
        def _us_only(a: dict[str, Any]) -> bool:
            h = _haystack(a)
            if _matches_markers(h, _ASIA_MARKERS) or _matches_markers(h, _EUROPE_MARKERS):
                return False
            return _matches_markers(h, _US_MARKERS) or "/news/articles/" in h
        return _us_only
    return None


def _feeds_for_edition(edition: str) -> list[tuple[str, str]]:
    """Return list of (section_key, feed_url)."""
    key = edition.strip().lower()
    if key in TOPIC_FEEDS:
        return [(key, TOPIC_FEEDS[key])]
    if key in ("global", "all", ""):
        return [(k, TOPIC_FEEDS[k]) for k in GLOBAL_FEED_KEYS]
    # Regional editions: aggregate global feeds + filter
    if key in ("asia", "europe", "us", "usa", "americas"):
        return [(k, TOPIC_FEEDS[k]) for k in GLOBAL_FEED_KEYS]
    return [(k, TOPIC_FEEDS[k]) for k in GLOBAL_FEED_KEYS]


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(text, "html.parser").get_text(" ")).strip()


def _entry_body(entry: Any) -> str:
    parts: list[str] = []
    summary = getattr(entry, "summary", "") or ""
    if summary:
        parts.append(_strip_html(summary))
    content = getattr(entry, "content", None)
    if content:
        for block in content[:2]:
            val = block.get("value") if isinstance(block, dict) else getattr(block, "value", "")
            if val:
                text = _strip_html(str(val))
                if text and text not in parts and not text.lower().startswith("photographer:"):
                    parts.append(text)
    return "\n\n".join(parts).strip()


def _parse_feed_entry(entry: Any, *, section: str, edition: str) -> dict[str, Any] | None:
    url = str(getattr(entry, "link", "") or "").strip()
    if not url or "bloomberg.com" not in url.lower():
        return None
    title = str(getattr(entry, "title", "") or "").strip()
    body = _entry_body(entry)
    if not title and not body:
        return None
    return normalize_article(
        {
            "title": title,
            "url": url,
            "body": body,
            "date": getattr(entry, "published", "") or getattr(entry, "updated", ""),
            "author": getattr(entry, "author", ""),
            "section": section,
            "edition": edition,
        },
        provider="bloomberg_own",
    )


def _parse_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            typ = str(item.get("@type") or "")
            if "NewsArticle" in typ or "Article" in typ:
                return item
    return {}


def parse_article_html(html: str, url: str = "", edition: str = "") -> dict[str, Any]:
    """Parse Bloomberg article HTML when accessible (often 403)."""
    soup = BeautifulSoup(html, "html.parser")
    ld = _parse_json_ld(soup)

    og = soup.find("meta", property="og:title")
    title = (
        str(ld.get("headline") or ld.get("name") or "")
        or (str(og["content"]).strip() if og and og.get("content") else "")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
    ).strip()

    body = ""
    ab = ld.get("articleBody")
    if isinstance(ab, str):
        body = _strip_html(ab)

    if len(body) < MIN_BODY_LEN:
        for sel in (
            "[data-component='article-body'] p",
            "article .body-copy p",
            ".article-body p",
            "div[data-module='ArticleBody'] p",
        ):
            nodes = soup.select(sel)
            if nodes:
                body = "\n\n".join(p.get_text(" ", strip=True) for p in nodes if p.get_text(strip=True))
                if len(body) >= MIN_BODY_LEN:
                    break

    date = str(ld.get("datePublished") or ld.get("dateModified") or "").strip()
    if not date:
        meta = soup.find("meta", property="article:published_time")
        if meta:
            date = str(meta.get("content") or "")

    return normalize_article(
        {"title": title, "url": url, "body": body, "date": date, "edition": edition},
        provider="bloomberg_own",
    )


class BloombergOwnScraper:
    """Bloomberg ingestion via RSS + optional HTML when not blocked."""

    def __init__(self, rate_limit_sec: float = 2.5):
        self.rate_limit_sec = max(0.5, float(rate_limit_sec))
        self._url_cache: dict[str, dict[str, Any]] = {}
        self._cache_at = 0.0
        self._cache_ttl = 1800.0

    async def _throttle(self) -> None:
        global _last_request_at
        async with _request_lock:
            elapsed = time.monotonic() - _last_request_at
            if elapsed < self.rate_limit_sec:
                await asyncio.sleep(self.rate_limit_sec - elapsed)
            _last_request_at = time.monotonic()

    async def _fetch_text(self, url: str) -> tuple[int, str]:
        await self._throttle()
        async with httpx.AsyncClient(
            timeout=35.0,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        ) as client:
            resp = await client.get(url)
            return resp.status_code, resp.text

    def _cache_put(self, articles: list[dict[str, Any]]) -> None:
        for art in articles:
            u = str(art.get("url") or "").strip()
            if u:
                self._url_cache[u] = art
        self._cache_at = time.monotonic()

    def _cache_get(self, url: str) -> dict[str, Any] | None:
        if time.monotonic() - self._cache_at > self._cache_ttl:
            self._url_cache.clear()
            return None
        return self._url_cache.get(url)

    async def _fetch_feed_articles(
        self,
        edition: str,
        *,
        max_items: int,
    ) -> list[dict[str, Any]]:
        feeds = _feeds_for_edition(edition)
        filt = _edition_filter(edition)
        best: dict[str, dict[str, Any]] = {}

        for section, feed_url in feeds:
            try:
                status, text = await self._fetch_text(feed_url)
                if status != 200:
                    logger.warning("Bloomberg RSS %s HTTP %s", section, status)
                    continue
                feed = feedparser.parse(text)
                for entry in feed.entries:
                    art = _parse_feed_entry(entry, section=section, edition=edition)
                    if not art or not art.get("url"):
                        continue
                    if filt and not filt(art):
                        continue
                    url = art["url"]
                    prev = best.get(url)
                    if prev is None or len(art.get("body") or "") > len(prev.get("body") or ""):
                        best[url] = art
            except Exception as exc:
                logger.warning("Bloomberg feed %s failed: %s", feed_url, exc)

        articles = sorted(
            best.values(),
            key=lambda a: str(a.get("date") or ""),
            reverse=True,
        )[:max_items]
        self._cache_put(articles)
        return articles

    async def fetch_latest(
        self,
        *,
        edition: str = "global",
        max_items: int = 15,
    ) -> dict[str, Any]:
        max_items = max(1, min(int(max_items), 50))
        articles = await self._fetch_feed_articles(edition, max_items=max_items)

        if not articles:
            return {
                "status": "error",
                "error": f"No s'han trobat articles Bloomberg per l'edició «{edition}»",
                "count": 0,
                "articles": [],
                "edition": edition,
            }

        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
            "provider": "bloomberg_own",
            "edition": edition,
            "message": f"{len(articles)} articles Bloomberg ({edition}) via RSS oficial",
        }

    async def scrape_url(self, url: str, *, edition: str = "global") -> dict[str, Any] | None:
        if not is_bloomberg_url(url):
            return None

        cached = self._cache_get(url)
        if cached and len(cached.get("body") or "") >= MIN_BODY_LEN:
            return cached

        try:
            status, html = await self._fetch_text(url)
            if status == 200 and "captcha" not in html.lower() and "robot" not in html.lower():
                art = parse_article_html(html, url, edition=edition)
                if art.get("title") or len(art.get("body") or "") >= MIN_BODY_LEN:
                    self._url_cache[url] = art
                    return art
        except Exception as exc:
            logger.warning("Bloomberg HTML %s: %s", url, exc)

        # Fallback: refresh feeds and find URL
        await self._fetch_feed_articles(edition, max_items=80)
        return self._cache_get(url)

    async def scrape_urls(
        self,
        urls: list[str],
        *,
        edition: str = "global",
        max_items: int = 10,
    ) -> dict[str, Any]:
        clean = [u.strip() for u in urls if u and is_bloomberg_url(u.strip())]
        if not clean:
            return {
                "status": "error",
                "error": "Cap URL vàlida de bloomberg.com",
                "count": 0,
                "articles": [],
            }

        await self._fetch_feed_articles(edition, max_items=60)
        articles: list[dict[str, Any]] = []
        for url in clean[:max_items]:
            art = await self.scrape_url(url, edition=edition)
            if art:
                articles.append(art)
            else:
                articles.append(
                    normalize_article(
                        {
                            "title": url.split("/")[-1].replace("-", " ")[:120],
                            "url": url,
                            "body": "",
                            "edition": edition,
                        },
                        provider="bloomberg_own",
                    )
                )

        articles = [a for a in articles if a.get("title") or a.get("body")]
        thin = sum(1 for a in articles if len(a.get("body") or "") < MIN_BODY_LEN)
        msg = f"{len(articles)} articles Bloomberg"
        if thin:
            msg += (
                f" ({thin} amb text limitat — Bloomberg bloqueja scraping HTML; "
                "usa mode «latest» per RSS amb resum)"
            )

        return {
            "status": "success" if articles else "error",
            "count": len(articles),
            "articles": articles,
            "provider": "bloomberg_own",
            "edition": edition,
            "message": msg,
            "paywall_note": (
                "Bloomberg.com retorna 403 a bots. El cos prové de feeds.bloomberg.com (RSS), "
                "no de l'article complet subscriptor."
            ),
        }
