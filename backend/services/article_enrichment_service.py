"""

Enrich OSINT articles with full body text before extraction.



Pipeline: GDELT/GFG snippets → Nikkei/Bloomberg scrapers → generic article fetcher.

"""

from __future__ import annotations



import logging

from typing import Any

from urllib.parse import urlparse



from app.config import settings

from integrations.article_fetcher import fetch_articles_batch, is_fetchable_url

from integrations.bloomberg_common import is_bloomberg_url

from integrations.bloomberg_service import BloombergService

from integrations.nikkei_common import is_nikkei_url

from integrations.nikkei_service import NikkeiService

from services.osint_data_utils import text_from_osint_item



logger = logging.getLogger(__name__)



MIN_ENRICH_TEXT = 200

MAX_NIKKEI_BATCH = 8

MAX_BLOOMBERG_BATCH = 8

MAX_GENERIC_BATCH = 12





def _preferred_domains() -> set[str]:

    raw = getattr(settings, "GEOPOLITICS_PREFERRED_DOMAINS", "") or ""

    return {d.strip().lower().replace("www.", "") for d in raw.split(",") if d.strip()}





def _domain(url: str) -> str:

    try:

        return urlparse(url).netloc.lower().replace("www.", "")

    except Exception:

        return ""





def _priority(item: dict[str, Any]) -> float:

    score = float(item.get("frontpage_score") or item.get("importance_score") or 0)

    dom = _domain(str(item.get("url") or ""))

    if dom in _preferred_domains():

        score += 10.0

    return score





def _merge_scraped(item: dict[str, Any], scraped: dict[str, Any]) -> dict[str, Any]:

    merged = {**item}

    body = str(scraped.get("body") or scraped.get("summary") or "").strip()

    if body:

        merged["body"] = body

        merged["summary"] = body[:500]

        merged["enriched"] = True

        merged["enrichment_source"] = scraped.get("provider") or scraped.get(

            "enrichment_source", "fetcher"

        )

    if scraped.get("title") and not merged.get("title"):

        merged["title"] = scraped["title"]

    if scraped.get("authors"):

        merged["authors"] = scraped["authors"]

    if scraped.get("date") and not merged.get("date"):

        merged["date"] = scraped["date"]

    return merged





async def enrich_osint_items(

    items: list[dict[str, Any]],

    *,

    min_text_len: int = MIN_ENRICH_TEXT,

) -> list[dict[str, Any]]:

    """

    Return items with enriched summary/body where possible.

    Priority: Nikkei → Bloomberg → generic HTTP fetcher.

    """

    if not items:

        return items



    nikkei_svc = NikkeiService()

    bloomberg_svc = BloombergService()



    thin: list[dict[str, Any]] = []

    for item in items:

        url = str(item.get("url") or "").strip()

        if not url:

            continue

        if len(text_from_osint_item(item).strip()) >= min_text_len:

            continue

        thin.append(item)



    if not thin:

        return items



    thin.sort(key=_priority, reverse=True)



    nikkei_urls: list[str] = []

    bloomberg_urls: list[str] = []

    generic_urls: list[str] = []



    for item in thin:

        url = str(item.get("url") or "").strip()

        if is_nikkei_url(url) and nikkei_svc.can_enrich:

            nikkei_urls.append(url)

        elif is_bloomberg_url(url):

            bloomberg_urls.append(url)

        elif is_fetchable_url(url):

            generic_urls.append(url)



    by_url: dict[str, dict[str, Any]] = {}



    if nikkei_urls:

        unique = list(dict.fromkeys(nikkei_urls))[:MAX_NIKKEI_BATCH]

        logger.info("Enriching %d Nikkei URLs", len(unique))

        result = await nikkei_svc.scrape_urls(unique, max_items=MAX_NIKKEI_BATCH)

        if result.get("status") == "success":

            for a in result.get("articles") or []:

                if a.get("url"):

                    by_url[str(a["url"]).strip()] = a

        else:

            logger.warning("Nikkei enrichment failed: %s", result.get("error"))



    if bloomberg_urls:

        unique_bb = list(dict.fromkeys(bloomberg_urls))[:MAX_BLOOMBERG_BATCH]

        logger.info("Enriching %d Bloomberg URLs", len(unique_bb))

        bb_result = await bloomberg_svc.scrape_urls(unique_bb, max_items=MAX_BLOOMBERG_BATCH)

        if bb_result.get("status") == "success":

            for a in bb_result.get("articles") or []:

                if a.get("url"):

                    by_url[str(a["url"]).strip()] = a

        else:

            logger.warning("Bloomberg enrichment failed: %s", bb_result.get("error"))



    remaining_generic = [u for u in generic_urls if u not in by_url]

    if remaining_generic:

        unique_gen = list(dict.fromkeys(remaining_generic))[:MAX_GENERIC_BATCH]

        logger.info("Generic fetcher: %d URLs", len(unique_gen))

        fetched = await fetch_articles_batch(unique_gen, max_items=MAX_GENERIC_BATCH)

        by_url.update(fetched)

    remaining_thin = [
        str(item.get("url") or "").strip()
        for item in thin
        if str(item.get("url") or "").strip() not in by_url
        or len(text_from_osint_item(by_url.get(str(item.get("url") or "").strip(), {})).strip())
        < min_text_len
    ]
    if remaining_thin:
        from integrations.tavily_api import TavilyAPIService

        tavily = TavilyAPIService()
        if tavily.configured():
            unique_tavily = list(dict.fromkeys(remaining_thin))[:8]
            logger.info("Tavily extract fallback: %d URLs", len(unique_tavily))
            tavily_result = await tavily.extract(unique_tavily)
            if tavily_result.get("status") == "success":
                for a in tavily_result.get("articles") or []:
                    if a.get("url"):
                        by_url[str(a["url"]).strip()] = a
            else:
                logger.warning("Tavily extract failed: %s", tavily_result.get("error"))

    if not by_url:

        return items



    enriched: list[dict[str, Any]] = []

    for item in items:

        url = str(item.get("url") or "").strip()

        scraped = by_url.get(url)

        if not scraped:

            enriched.append(item)

            continue

        enriched.append(_merge_scraped(item, scraped))



    return enriched





async def enrich_single_article(item: dict[str, Any], *, min_text_len: int = MIN_ENRICH_TEXT) -> dict[str, Any]:

    """Enrich one article dict (alert match, manual extract)."""

    if len(text_from_osint_item(item).strip()) >= min_text_len:

        return item

    result = await enrich_osint_items([item], min_text_len=min_text_len)

    return result[0] if result else item


