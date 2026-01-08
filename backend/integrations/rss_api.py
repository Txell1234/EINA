"""
RSS/Atom feed integration
"""
from typing import Dict, Any, Optional, List
from xml.etree import ElementTree
import httpx


class RSSFeedService:
    """Fetch and parse RSS/Atom feeds for OSINT"""

    async def fetch_feed(
        self,
        feed_url: str,
        limit: int = 20,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch RSS/Atom feed and optionally filter by keywords"""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(feed_url)
                response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            channel = root.find("channel")
            entries = []

            if channel is not None:
                source = channel.findtext("title")
                items = channel.findall("item")
                for item in items:
                    entries.append({
                        "title": item.findtext("title"),
                        "link": item.findtext("link"),
                        "published": item.findtext("pubDate"),
                        "summary": item.findtext("description"),
                        "source": source,
                    })
            else:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                source = root.findtext("atom:title", default=None, namespaces=ns)
                items = root.findall("atom:entry", namespaces=ns)
                for item in items:
                    link = None
                    link_el = item.find("atom:link", namespaces=ns)
                    if link_el is not None:
                        link = link_el.attrib.get("href")
                    summary = item.findtext("atom:summary", default=None, namespaces=ns)
                    if summary is None:
                        summary = item.findtext("atom:content", default=None, namespaces=ns)
                    entries.append({
                        "title": item.findtext("atom:title", default=None, namespaces=ns),
                        "link": link,
                        "published": item.findtext("atom:updated", default=None, namespaces=ns),
                        "summary": summary,
                        "source": source,
                    })

            if keywords:
                lower_keywords = [kw.lower() for kw in keywords]
                filtered = []
                for entry in entries:
                    haystack = " ".join(
                        str(entry.get(field, "")) for field in ["title", "summary"]
                    ).lower()
                    if any(kw in haystack for kw in lower_keywords):
                        filtered.append(entry)
                entries = filtered

            results = entries[:limit]
            source_name = results[0]["source"] if results else None

            return {
                "status": "success",
                "source": source_name,
                "entries": results,
                "count": len(results),
            }
        except httpx.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP error: {str(e)}",
                "entries": [],
            }
        except ElementTree.ParseError as e:
            return {
                "status": "error",
                "error": f"XML parse error: {str(e)}",
                "entries": [],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "entries": [],
            }
