"""Score OSINT articles and statements against a case's thematic focus."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from services.osint_data_utils import _GEO_TERMS, _strip_accents

_THEMATIC_CLUSTERS: dict[str, list[str]] = {
    "rearmament": [
        "rearmament",
        "rearmament",
        "rearmer",
        "jsdf",
        "self-defense",
        "self defence",
        "self-defence",
        "article 9",
        "article nine",
        "defense budget",
        "defence budget",
        "military buildup",
        "pacifist constitution",
        "collective self-defense",
    ],
    "indo_pacific": [
        "indo-pacific",
        "indopacific",
        "quad",
        "aukus",
        "first island chain",
        "south china sea",
    ],
    "sanctions": ["sanction", "sanctions", "embargo", "export control"],
    "diplomacy": ["diplomacy", "diplomatic", "mediation", "bilateral", "multilateral"],
    "regulatory": [
        "regulatory",
        "regulation",
        "compliance",
        "licence",
        "license",
        "rulemaking",
        "export control",
    ],
    "supply_chain": [
        "supply chain",
        "dependency",
        "semiconductor",
        "critical mineral",
        "industrial policy",
        "reshoring",
    ],
    "market_entry": [
        "market entry",
        "capex",
        "foreign direct investment",
        "fdi",
        "joint venture",
        "local content",
    ],
    "energy": ["energy security", "lng", "pipeline", "opec", "renewable"],
    "defense_procurement": ["procurement", "arms sale", "defense contract", "offset"],
}

# Topics common in think-tank feeds but often off-focus for regional cases
_DISTRACTOR_CLUSTERS: dict[str, list[str]] = {
    "iran_gulf": [
        "iran",
        "irgc",
        "hormuz",
        "tehran",
        "persian gulf",
        "revolutionary guard",
    ],
    "vatican_religion": [
        "pope",
        "vatican",
        "holy see",
        "leo xiv",
        "john paul",
        "catholic church",
        "nuncio",
    ],
    "us_domestic": [
        "deportation",
        "noncriminal immigrant",
        "wall street",
    ],
}

_GENERIC_STOP = frozenset(
    """
    cas case analisi analysis factors factor estudi estudiar sobre del de la els les
    the and for with from this that these those geopolitic geopolitical intelligence
    tots all every each nivel level nivell regio region regional implic implica
    factor factors trobada meeting summit amb with com com que per les els
    """.split()
)

_YEAR_TOKEN = re.compile(r"^(19|20)\d{2}s?$")
_NUMERIC_HEAVY = re.compile(r"^\d+[-–/]\d+|\d{2,}nm$")


def _is_noise_token(tok: str) -> bool:
    t = _strip_accents(tok.lower())
    if len(t) < 4:
        return True
    if t in _GENERIC_STOP:
        return True
    if _YEAR_TOKEN.match(t) or _NUMERIC_HEAVY.match(t):
        return True
    if sum(c.isdigit() for c in t) / max(len(t), 1) > 0.45:
        return True
    return False


@dataclass
class CaseTopicProfile:
    focus_label: str
    keywords: set[str] = field(default_factory=set)
    primary_geos: set[str] = field(default_factory=set)
    themes: set[str] = field(default_factory=set)
    raw_text: str = ""


def _tokenize(text: str) -> list[str]:
    lower = _strip_accents((text or "").lower())
    return re.findall(r"[a-z0-9][a-z0-9\-']{2,}", lower)


def build_case_topic_profile(
    case_name: str,
    case_description: str = "",
    extra_context: str = "",
) -> CaseTopicProfile:
    raw = " ".join(filter(None, [case_name, case_description, extra_context])).strip()
    lower = _strip_accents(raw.lower())
    # Geo/theme detection uses full briefing; generic tokens only from the focus header
    focus_snippet = " ".join(
        filter(None, [case_name, (case_description or "")[:500], (extra_context or "")[:300]])
    ).strip()

    keywords: set[str] = set()
    primary_geos: set[str] = set()
    themes: set[str] = set()

    for local, english in _GEO_TERMS.items():
        local_n = _strip_accents(local)
        if local_n in lower or english.lower() in lower:
            primary_geos.add(local)
            primary_geos.add(english.lower())
            keywords.add(local_n)
            keywords.add(english.lower())

    for theme, terms in _THEMATIC_CLUSTERS.items():
        if any(_strip_accents(t) in lower for t in terms):
            themes.add(theme)
            for t in terms:
                if len(t) >= 5 and not _is_noise_token(t):
                    keywords.add(_strip_accents(t))

    # Proper nouns / capitalized entities (Trump, Xi, NATO…)
    for entity in re.findall(
        r"\b[A-ZÀ-ÿ][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]{2,})?", focus_snippet
    ):
        norm = _strip_accents(entity.lower())
        if not _is_noise_token(norm):
            keywords.add(norm)

    for tok in _tokenize(focus_snippet):
        if _is_noise_token(tok):
            continue
        keywords.add(tok)

    if not keywords and case_name:
        keywords.update(_tokenize(case_name))

    return CaseTopicProfile(
        focus_label=(case_name or "cas").strip()[:120],
        keywords=keywords,
        primary_geos=primary_geos,
        themes=themes,
        raw_text=raw[:500],
    )


def _count_hits(blob: str, terms: set[str] | list[str]) -> int:
    n = 0
    for term in terms:
        t = _strip_accents(str(term).lower())
        if len(t) < 3:
            continue
        if t in blob or re.search(rf"\b{re.escape(t)}\b", blob):
            n += 1
    return n


def score_text_relevance(
    text: str,
    title: str = "",
    profile: CaseTopicProfile | None = None,
) -> dict[str, Any]:
    """Return score 0..1 and diagnostic reasons."""
    if not profile or not profile.keywords:
        return {"score": 0.5, "reasons": ["sense_perfil_de_cas"], "distractors": []}

    blob = _strip_accents(f"{title} {text}".lower())
    kw_hits = _count_hits(blob, profile.keywords)
    geo_hits = _count_hits(blob, profile.primary_geos)

    score = 0.0
    reasons: list[str] = []

    if kw_hits:
        score += min(0.55, kw_hits * 0.12)
        reasons.append(f"{kw_hits} paraules clau del cas")
    if geo_hits:
        score += min(0.35, geo_hits * 0.18)
        reasons.append(f"{geo_hits} referències geogràfiques del focus")

    distractors: list[str] = []
    for cluster, terms in _DISTRACTOR_CLUSTERS.items():
        hits = _count_hits(blob, terms)
        if hits >= 2:
            distractors.append(cluster)
            if geo_hits == 0 and kw_hits <= 1:
                score -= min(0.45, hits * 0.12)

    if profile.themes:
        theme_terms: list[str] = []
        for th in profile.themes:
            theme_terms.extend(_THEMATIC_CLUSTERS.get(th, []))
        thits = _count_hits(blob, theme_terms)
        if thits:
            score += min(0.25, thits * 0.1)
            reasons.append(f"temàtica {', '.join(sorted(profile.themes))}")

    score = max(0.0, min(1.0, score))

    if not reasons and score < 0.2:
        reasons.append("sense coincidències amb el focus del cas")

    return {
        "score": round(score, 3),
        "reasons": reasons,
        "distractors": distractors,
        "keyword_hits": kw_hits,
        "geo_hits": geo_hits,
    }


def score_statement_relevance(
    *,
    statement: str,
    actor: str = "",
    topic: str = "",
    context: str = "",
    profile: CaseTopicProfile | None = None,
) -> dict[str, Any]:
    blob = " ".join(filter(None, [actor, topic, context, statement]))
    return score_text_relevance(blob, profile=profile)


def is_article_on_topic(
    text: str,
    title: str = "",
    profile: CaseTopicProfile | None = None,
    *,
    min_score: float = 0.28,
) -> bool:
    return score_text_relevance(text, title, profile)["score"] >= min_score


def is_statement_on_topic(
    *,
    statement: str,
    actor: str = "",
    topic: str = "",
    context: str = "",
    profile: CaseTopicProfile | None = None,
    min_score: float = 0.22,
) -> bool:
    return score_statement_relevance(
        statement=statement,
        actor=actor,
        topic=topic,
        context=context,
        profile=profile,
    )["score"] >= min_score
