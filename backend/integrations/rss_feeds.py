"""
RSS Feeds from think-tanks, governments, and international organizations.
No API key required.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "iiss": {"url": "https://www.iiss.org/rss/latest-analysis", "category": "defence"},
    "chatham_house": {"url": "https://www.chathamhouse.org/rss.xml", "category": "geopolitics"},
    "rand": {"url": "https://www.rand.org/blog.xml", "category": "policy"},
    "cfr": {"url": "https://www.cfr.org/rss.xml", "category": "geopolitics"},
    "csis": {"url": "https://www.csis.org/rss.xml", "category": "security"},
    "icg": {"url": "https://www.crisisgroup.org/rss.xml", "category": "conflict"},
    "brookings": {"url": "https://www.brookings.edu/feed/", "category": "policy"},
    "elcano": {"url": "https://www.realinstitutoelcano.org/rss/", "category": "geopolitics"},
    "foreign_affairs": {"url": "https://www.foreignaffairs.com/rss.xml", "category": "geopolitics"},
    "ecfr": {"url": "https://ecfr.eu/feed/", "category": "eu_foreign"},
}


class RSSFeedsService:
    async def fetch_feed(self, source_key: str, max_items: int = 20) -> dict[str, Any]:
        if source_key not in RSS_SOURCES:
            return {"status": "error", "message": f"Unknown source: {source_key}"}
        source = RSS_SOURCES[source_key]
        try:
            import feedparser

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    source["url"], headers={"User-Agent": "EINA-OSINT/1.0"}
                )
                resp.raise_for_status()
            feed = feedparser.parse(resp.text)
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
            return {"status": "success", "source": source_key, "count": len(items), "items": items}
        except ImportError:
            return {
                "status": "error",
                "message": "feedparser not installed. Run: pip install feedparser",
            }
        except Exception as e:
            logger.error("RSS error for %s: %s", source_key, e)
            return {"status": "error", "message": str(e), "source": source_key, "count": 0, "items": []}

    async def fetch_all(self, max_items_per_feed: int = 10) -> dict[str, Any]:
        results = {}
        for key in RSS_SOURCES:
            results[key] = await self.fetch_feed(key, max_items_per_feed)
        total = sum(r.get("count", 0) for r in results.values())
        return {"status": "success", "total": total, "sources": results}

    def get_available_sources(self) -> list[dict]:
        return [{"key": k, "url": v["url"], "category": v["category"]} for k, v in RSS_SOURCES.items()]
