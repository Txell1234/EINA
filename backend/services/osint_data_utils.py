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
    Uses case topic profile (geos, themes, entities) instead of raw token soup.
    """
    from services.case_topic_relevance import build_case_topic_profile

    combined = f"{case_name} {query}".strip()
    if not combined:
        return "geopolitics"

    profile = build_case_topic_profile(case_name, query, "")
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(word: str) -> None:
        w = word.strip()
        if not w:
            return
        key = _strip_accents(w.lower())
        if key in seen or len(key) < 3:
            return
        seen.add(key)
        tokens.append(w)

    # English geo names first — prioritize geos mentioned in case name, cap at 3
    lower = _strip_accents(combined.lower())
    name_lower = _strip_accents(case_name.lower())
    geo_hits: list[str] = []
    for local, english in _GEO_TERMS.items():
        local_n = _strip_accents(local)
        if local_n in lower or english.lower() in lower:
            geo_hits.append((local_n in name_lower or english.lower() in name_lower, english))
    geo_hits.sort(key=lambda x: (not x[0], x[1]))
    for _, english in geo_hits[:3]:
        _add(english)

    # One thematic anchor
    theme_priority = [
        "rearmament",
        "military buildup",
        "defense budget",
        "indo-pacific",
        "geoeconomic",
        "sanctions",
        "diplomatic",
        "geopolitical",
    ]
    for term in theme_priority:
        if _strip_accents(term) in lower:
            _add(term)
            break

    # Named entities (Trump, Xi…) — max 2
    entity_added = 0
    for kw in sorted(profile.keywords, key=len, reverse=True):
        if entity_added >= 2:
            break
        if any(c.isdigit() for c in kw):
            continue
        if kw in profile.primary_geos or _strip_accents(kw) in {
            _strip_accents(g) for g in profile.primary_geos
        }:
            continue
        if len(kw) >= 4 and " " in kw or (len(kw) >= 5 and kw.isalpha()):
            _add(kw)
            entity_added += 1
        if len(tokens) >= max_words:
            return " ".join(tokens[:max_words])

    # Residual meaningful tokens from case name
    for raw in re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-']*", case_name):
        norm = _strip_accents(raw.lower())
        if len(norm) >= 4 and norm not in _STOPWORDS and not raw.isupper():
            _add(raw if raw[0].isupper() else norm)
        if len(tokens) >= max_words:
            break

    if not tokens:
        fallback = normalize_search_query(combined, max_len=80)
        return fallback or "geopolitics"

    return " ".join(tokens[:max_words])


def _rank_geos_for_case(case_name: str, description: str, geos: list[str]) -> list[str]:
    """Prioritize geos mentioned in case title, then description header."""
    name_l = _strip_accents(case_name.lower())
    head_l = _strip_accents((description or "")[:400].lower())

    def priority(english: str) -> tuple[int, str]:
        for local, eng in _GEO_TERMS.items():
            if eng != english:
                continue
            local_n = _strip_accents(local)
            if local_n in name_l or eng.lower() in name_l:
                return (0, english)
            if local_n in head_l or eng.lower() in head_l:
                return (1, english)
        return (2, english)

    return sorted(geos, key=priority)


def build_primary_osint_query(
    case_name: str,
    case_description: str = "",
    extra_context: str = "",
    *,
    max_words: int = 8,
) -> str:
    """Single best OSINT query: primary geo from case focus + main theme + key entity."""
    raw = " ".join(filter(None, [case_name, case_description, extra_context])).strip()
    if not raw:
        return "geopolitics"

    lower = _strip_accents(raw.lower())
    en_geos: list[str] = []
    for local, english in _GEO_TERMS.items():
        if _strip_accents(local) in lower or english.lower() in lower:
            if english not in en_geos:
                en_geos.append(english)
    en_geos = _rank_geos_for_case(case_name, case_description, en_geos)

    theme: str | None = None
    for term in (
        "rearmament",
        "military buildup",
        "defense budget",
        "indo-pacific",
        "geoeconomic",
        "sanctions",
        "diplomatic",
    ):
        if _strip_accents(term) in lower:
            theme = term
            break

    parts: list[str] = []
    if en_geos:
        parts.append(en_geos[0])
    if theme:
        parts.append(theme)
    if "trump" in lower and ("xi" in lower or "china" in lower or "xina" in lower):
        parts.extend(["Trump", "Xi"])

    if parts:
        return normalize_search_query(" ".join(parts), max_len=120)

    return extract_search_keywords(
        f"{case_description} {extra_context}".strip(),
        case_name,
        max_words=max_words,
    )


def build_osint_search_queries(
    case_name: str,
    case_description: str = "",
    extra_context: str = "",
    *,
    max_queries: int = 3,
    max_words: int = 8,
) -> list[str]:
    """Build 1–3 focused OSINT queries from case premise/description."""
    from services.case_topic_relevance import build_case_topic_profile

    raw = " ".join(filter(None, [case_name, case_description, extra_context])).strip()
    if not raw:
        return ["geopolitics"]

    primary = build_primary_osint_query(
        case_name, case_description, extra_context, max_words=max_words
    )
    queries: list[str] = [primary]
    seen = {_strip_accents(primary.lower())}

    lower = _strip_accents(raw.lower())
    en_geos: list[str] = []
    for local, english in _GEO_TERMS.items():
        if _strip_accents(local) in lower or english.lower() in lower:
            if english not in en_geos:
                en_geos.append(english)
    en_geos = _rank_geos_for_case(case_name, case_description, en_geos)

    def _push(q: str) -> None:
        key = _strip_accents(q.lower())
        if q and key not in seen:
            seen.add(key)
            queries.append(q)

    if "trump" in lower and ("xi" in lower or "china" in lower or "xina" in lower):
        _push(
            normalize_search_query(
                f"Trump Xi geoeconomic {en_geos[0] if en_geos else ''}".strip(),
                max_len=120,
            )
        )

    if len(en_geos) >= 2:
        alt = extract_search_keywords(
            f"{case_description} {extra_context}".strip(),
            case_name,
            max_words=max_words,
        )
        _push(alt)

    return queries[:max_queries]


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

    out: dict[str, Any] = {
        "title": title,
        "url": url,
        "date": date,
        "source": source,
        "summary": summary[:500] if summary else "",
    }
    for extra in (
        "body",
        "frontpage_score",
        "importance_score",
        "link_percent_max_id",
        "from_frontpage_url",
        "link_text",
        "authors",
        "enriched",
        "enrichment_source",
    ):
        if raw.get(extra) is not None:
            out[extra] = raw.get(extra)
    return out


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
