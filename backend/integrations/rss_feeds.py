"""
RSS Feeds from think-tanks, governments, and international organizations.
No API key required.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "EINA-OSINT/1.0 (RSS reader; +https://github.com/eina-osint)"

RSS_SOURCES = {
    "iiss": {"url": "https://www.iiss.org/rss/latest-analysis", "category": "defence"},
    "chatham_house": {"url": "https://www.chathamhouse.org/rss.xml", "category": "geopolitics"},
    "rand": {"url": "https://www.rand.org/blog.xml", "category": "policy"},
    "cfr": {
        "url": "https://www.cfr.org/rss/feed.xml",
        "fallback_urls": [
            "https://www.cfr.org/rss.xml",
            "https://www.cfr.org/rss/feed",
        ],
        "category": "geopolitics",
    },
    "csis": {"url": "https://www.csis.org/rss.xml", "category": "security"},
    "icg": {"url": "https://www.crisisgroup.org/rss.xml", "category": "conflict"},
    "brookings": {"url": "https://www.brookings.edu/feed/", "category": "policy"},
    "elcano": {"url": "https://www.realinstitutoelcano.org/rss/", "category": "geopolitics"},
    "foreign_affairs": {"url": "https://www.foreignaffairs.com/rss.xml", "category": "geopolitics"},
    "ecfr": {"url": "https://ecfr.eu/feed/", "category": "eu_foreign"},
}

# Fonts curades per tema (Substack, mitjans especialitzats) — patró china-us-rhetoric
CURATED_TOPIC_FEEDS: dict[str, list[dict[str, str]]] = {
    "china": [
        {
            "url": "https://trackingpeoplesdaily.substack.com/feed",
            "label": "Tracking People's Daily (Substack)",
            "category": "geopolitics",
        },
        {
            "url": "https://www.csis.org/rss.xml",
            "label": "CSIS",
            "category": "security",
        },
    ],
    "japan": [
        {
            "url": "https://www.japantimes.co.jp/feed/",
            "label": "Japan Times",
            "category": "geopolitics",
        },
        {
            "url": "https://www.iiss.org/rss/latest-analysis",
            "label": "IISS",
            "category": "defence",
        },
    ],
    "indo_pacific": [
        {
            "url": "https://www.csis.org/rss.xml",
            "label": "CSIS",
            "category": "security",
        },
        {
            "url": "https://www.realinstitutoelcano.org/rss/",
            "label": "Elcano",
            "category": "geopolitics",
        },
    ],
    "europe": [
        {"url": "https://ecfr.eu/feed/", "label": "ECFR", "category": "eu_foreign"},
        {"url": "https://www.chathamhouse.org/rss.xml", "label": "Chatham House", "category": "geopolitics"},
    ],
    "ukraine": [
        {
            "url": "https://www.crisisgroup.org/rss.xml",
            "label": "International Crisis Group",
            "category": "conflict",
        },
    ],
}

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "china": ["china", "xina", "chinese", "bri", "beijing", "taiwan"],
    "japan": ["japan", "japó", "japon", "tokyo", "rearmament", "reamament"],
    "indo_pacific": ["indo-pacific", "indopacific", "quad", "aukus", "pacific"],
    "europe": ["europe", "europa", "eu ", "unió europea", "union europea"],
    "ukraine": ["ukraine", "ucraïna", "ucraina", "russia", "rússia"],
}


def match_curated_feeds(case_name: str, case_description: str = "", max_feeds: int = 3) -> list[dict[str, str]]:
    """Select curated RSS/Substack feeds from case text (china-us-rhetoric style)."""
    text = f"{case_name} {case_description}".lower()
    matched: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for topic, keywords in TOPIC_KEYWORDS.items():
        if not any(kw in text for kw in keywords):
            continue
        for feed in CURATED_TOPIC_FEEDS.get(topic, []):
            url = feed["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            matched.append(feed)
            if len(matched) >= max_feeds:
                return matched
    return matched


class RSSFeedsService:
    async def _fetch_url(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.text

    async def fetch_feed(self, source_key: str, max_items: int = 20) -> dict[str, Any]:
        if source_key not in RSS_SOURCES:
            return {
                "status": "error",
                "error": f"Font desconeguda: {source_key}",
                "message": f"Unknown source: {source_key}",
                "count": 0,
                "items": [],
            }
        source = RSS_SOURCES[source_key]
        urls_to_try = [source["url"]] + list(source.get("fallback_urls") or [])

        try:
            import feedparser
        except ImportError:
            return {
                "status": "error",
                "error": "feedparser not installed. Run: pip install feedparser",
                "message": "feedparser not installed",
                "count": 0,
                "items": [],
            }

        last_error: Exception | None = None
        for feed_url in urls_to_try:
            try:
                text = await self._fetch_url(feed_url)
                feed = feedparser.parse(text)
                if feed.bozo and not feed.entries:
                    raise ValueError(f"Feed invàlid o buit ({feed_url})")
                items = []
                for entry in feed.entries[:max_items]:
                    items.append(
                        {
                            "title": getattr(entry, "title", ""),
                            "url": getattr(entry, "link", ""),
                            "summary": getattr(entry, "summary", "")[:500],
                            "date": getattr(entry, "published", ""),
                            "source": source_key,
                            "category": source["category"],
                        }
                    )
                return {
                    "status": "success",
                    "source": source_key,
                    "feed_url": feed_url,
                    "count": len(items),
                    "items": items,
                }
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "RSS HTTP %s per %s (%s)",
                    e.response.status_code,
                    source_key,
                    feed_url,
                )
            except Exception as e:
                last_error = e
                logger.warning("RSS error for %s (%s): %s", source_key, feed_url, e)

        status_code = getattr(getattr(last_error, "response", None), "status_code", None)
        msg = str(last_error) if last_error else "Error desconegut"
        return {
            "status": "error",
            "error": f"No s'ha pogut llegir el feed {source_key}"
            + (f" (HTTP {status_code})" if status_code else f": {msg}"),
            "message": msg,
            "source": source_key,
            "count": 0,
            "items": [],
        }

    async def fetch_url(
        self,
        feed_url: str,
        max_items: int = 20,
        source_label: str = "custom",
        category: str = "curated",
    ) -> dict[str, Any]:
        """Fetch any RSS/Atom/Substack feed URL (curated source per case)."""
        feed_url = (feed_url or "").strip()
        if not feed_url.startswith(("http://", "https://")):
            return {
                "status": "error",
                "error": "URL de feed invàlida",
                "message": "Invalid feed URL",
                "count": 0,
                "items": [],
            }

        try:
            import feedparser
        except ImportError:
            return {
                "status": "error",
                "error": "feedparser not installed",
                "message": "feedparser not installed",
                "count": 0,
                "items": [],
            }

        max_items = max(1, min(int(max_items), 40))
        try:
            text = await self._fetch_url(feed_url)
            feed = feedparser.parse(text)
            if feed.bozo and not feed.entries:
                return {
                    "status": "error",
                    "error": f"Feed buit o invàlid: {feed_url}",
                    "message": "Empty or invalid feed",
                    "feed_url": feed_url,
                    "count": 0,
                    "items": [],
                }
            items = []
            for entry in feed.entries[:max_items]:
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                content_parts = []
                if hasattr(entry, "content") and entry.content:
                    for block in entry.content[:2]:
                        if isinstance(block, dict) and block.get("value"):
                            content_parts.append(str(block["value"])[:2000])
                body = " ".join(content_parts) if content_parts else summary
                items.append(
                    {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "link", ""),
                        "summary": summary[:500],
                        "text": body[:3000],
                        "date": getattr(entry, "published", "") or getattr(entry, "updated", ""),
                        "source": source_label,
                        "category": category,
                    }
                )
            return {
                "status": "success",
                "source": source_label,
                "feed_url": feed_url,
                "count": len(items),
                "items": items,
                "provider": "rss_url",
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code} llegint {feed_url}",
                "message": str(e),
                "feed_url": feed_url,
                "count": 0,
                "items": [],
            }
        except Exception as e:
            logger.error("RSS URL error %s: %s", feed_url, e)
            return {
                "status": "error",
                "error": str(e),
                "message": str(e),
                "feed_url": feed_url,
                "count": 0,
                "items": [],
            }

    async def fetch_all(self, max_items_per_feed: int = 10) -> dict[str, Any]:
        results = {}
        for key in RSS_SOURCES:
            results[key] = await self.fetch_feed(key, max_items_per_feed)
        total = sum(r.get("count", 0) for r in results.values() if r.get("status") == "success")
        failed = sum(1 for r in results.values() if r.get("status") == "error")
        return {
            "status": "success" if total > 0 else "error",
            "total": total,
            "failed_feeds": failed,
            "sources": results,
        }

    def get_available_sources(self) -> list[dict]:
        sources = [{"key": k, "url": v["url"], "category": v["category"]} for k, v in RSS_SOURCES.items()]
        for topic, feeds in CURATED_TOPIC_FEEDS.items():
            for f in feeds:
                sources.append(
                    {
                        "key": f"curated_{topic}",
                        "url": f["url"],
                        "category": f.get("category", "curated"),
                        "label": f.get("label", topic),
                    }
                )
        return sources

    def list_curated_feeds(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for topic, feeds in CURATED_TOPIC_FEEDS.items():
            for f in feeds:
                out.append({"topic": topic, **f})
        return out
