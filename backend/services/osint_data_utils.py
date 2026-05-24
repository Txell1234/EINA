"""
Shared utilities to normalize OSINT payloads and flatten nested results
(NewsAPI, GDELT, RSS, rss_all) into a uniform list of articles.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of with by from as is are was were be been
    being have has had do does did will would could should may might must shall can
    el la los las un una unos unas y o de del en con por para que es son fue eren
    ser estar ha han hecho todo todos tots tota totes els les i o en de amb per
    sobre sobre els factors analisis analisis geopolitic trobada focus foculaitzacio
    reamrament factors factor
    """.split()
)

_GEO_TERMS = {
    "japó": "Japan",
    "japon": "Japan",
    "japo": "Japan",
    "japón": "Japan",
    "xina": "China",
    "china": "China",
    "espanya": "Spain",
    "spain": "Spain",
    "estats units": "United States",
    "eua": "United States",
    "ue": "European Union",
    "unió europea": "European Union",
    "rússia": "Russia",
    "russia": "Russia",
    "ucraïna": "Ukraine",
    "ucraina": "Ukraine",
    "taiwan": "Taiwan",
    "corea": "Korea",
    "indopacífic": "Indo-Pacific",
    "indopacific": "Indo-Pacific",
}


def normalize_search_query(query: str, max_len: int = 120) -> str:
    """Trim, collapse whitespace, and cap length for search APIs."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    if len(q) > max_len:
        q = q[:max_len].rsplit(" ", 1)[0]
    return q.strip()


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extract_search_keywords(query: str, case_name: str = "", max_words: int = 10) -> str:
    """
    Reduce long briefing text to short keyword query for OSINT APIs.
    Prefers case_name tokens and known geo terms.
    """
    combined = f"{case_name} {query}".strip()
    lower = _strip_accents(combined.lower())

    geo_english: list[str] = []
    for local, english in _GEO_TERMS.items():
        if local in lower and english not in geo_english:
            geo_english.append(english)

    tokens: list[str] = list(geo_english)
    seen: set[str] = {w.lower() for w in tokens}

    for raw in re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-']*", combined):
        word = raw.lower()
        norm = _strip_accents(word)
        if len(norm) < 3 or norm in _STOPWORDS or word in seen or norm in seen:
            continue
        if raw.isupper() and len(raw) > 5:
            continue
        seen.add(word)
        seen.add(norm)
        tokens.append(raw if raw[0].isupper() and not raw.isupper() else norm)
        if len(tokens) >= max_words:
            break

    if not tokens:
        fallback = normalize_search_query(combined, max_len=80)
        return fallback or "geopolitics"

    return " ".join(tokens[:max_words])


def osint_has_error(data: Any) -> bool:
    if not isinstance(data, dict):
        return True
    if data.get("status") in ("error", "unavailable"):
        return True
    if data.get("error"):
        return True
    return False


def _normalize_item(raw: dict[str, Any], source_hint: str = "") -> dict[str, Any]:
    title = str(
        raw.get("title")
        or raw.get("name")
        or raw.get("headline")
        or ""
    ).strip()
    url = str(
        raw.get("url")
        or raw.get("link")
        or raw.get("source_url")
        or raw.get("permalink")
        or ""
    ).strip()
    date = str(
        raw.get("date")
        or raw.get("publishedAt")
        or raw.get("published")
        or raw.get("seendate")
        or raw.get("created_utc")
        or ""
    ).strip()
    summary = str(
        raw.get("summary")
        or raw.get("description")
        or raw.get("content")
        or raw.get("snippet")
        or raw.get("text")
        or raw.get("body")
        or ""
    ).strip()
    source = str(
        raw.get("source")
        or raw.get("domain")
        or raw.get("source_name")
        or source_hint
        or ""
    ).strip()
    if isinstance(raw.get("source"), dict):
        src_obj = raw["source"]
        source = source or str(src_obj.get("name") or src_obj.get("id") or "")

    return {
        "title": title,
        "url": url,
        "date": date,
        "source": source,
        "summary": summary[:500] if summary else "",
    }


def _items_from_list(items: list[Any], source_hint: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized = _normalize_item(item, source_hint)
            if normalized["title"] or normalized["url"] or normalized["summary"]:
                out.append(normalized)
    return out


def flatten_osint_items(data: Any) -> list[dict[str, Any]]:
    """
    Return [{title, url, date, source, summary}] from any OSINT result payload.
    Returns [] for error payloads or empty results.
    """
    if not isinstance(data, dict) or osint_has_error(data):
        return []

    items: list[dict[str, Any]] = []

    for key in ("articles", "items", "results"):
        raw_list = data.get(key)
        if isinstance(raw_list, list):
            items.extend(_items_from_list(raw_list, str(data.get("source") or "")))

    sources = data.get("sources")
    if isinstance(sources, dict):
        for source_key, source_data in sources.items():
            if not isinstance(source_data, dict):
                continue
            if osint_has_error(source_data):
                continue
            nested = source_data.get("items") or source_data.get("articles")
            if isinstance(nested, list):
                items.extend(_items_from_list(nested, source_key))

    if not items:
        root = _normalize_item(data)
        if root["title"] or root["url"] or root["summary"]:
            items.append(root)

    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = item.get("url") or item.get("title") or ""
        if key and key in seen_urls:
            continue
        if key:
            seen_urls.add(key)
        deduped.append(item)
    return deduped


def text_from_osint_item(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "description", "content", "text", "body"):
        val = item.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts).strip()


def text_from_osint_data(data: dict[str, Any]) -> str:
    """Aggregate text from all flattened items (legacy helper)."""
    parts = [text_from_osint_item(item) for item in flatten_osint_items(data)]
    return " ".join(p for p in parts if p)
