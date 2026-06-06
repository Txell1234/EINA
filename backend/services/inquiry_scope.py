"""Inquiry-driven OSINT scope — must-match terms, negative filters, directed queries."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.case_topic_relevance import (
    CaseTopicProfile,
    _DISTRACTOR_CLUSTERS,
    _THEMATIC_CLUSTERS,
    _count_hits,
    _strip_accents,
    build_case_topic_profile,
    score_text_relevance,
)

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "will",
        "would",
        "could",
        "should",
        "about",
        "before",
        "after",
        "when",
        "what",
        "which",
        "their",
        "there",
        "been",
        "have",
        "has",
        "had",
        "into",
        "over",
        "under",
        "between",
        "announces",
        "announce",
        "by",
        "per",
        "del",
        "les",
        "els",
        "que",
        "amb",
        "per",
        "una",
        "uns",
        "the",
    }
)

_HORIZON_RE = re.compile(
    r"\bby\s+("
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+\d{4}|"
    r"\d{4}|"
    r"q[1-4]\s+\d{4}|"
    r"\d+\s+months?"
    r")",
    re.I,
)

_ENTITY_RE = re.compile(r"\b([A-ZÀ-ÿ][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]{2,})?)\b")


@dataclass
class InquiryScopeProfile:
    """Scope derived from an analytical question — stricter than generic case profile."""

    question: str
    required_terms: list[str] = field(default_factory=list)
    min_required_matches: int = 2
    optional_terms: list[str] = field(default_factory=list)
    negative_terms: list[str] = field(default_factory=list)
    geo_focus: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    event_type: str = "geopolitical"
    horizon_label: str = ""
    horizon_end: str | None = None
    base_profile: CaseTopicProfile | None = None
    min_relevance: float = 0.40
    osint_queries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "required_terms": self.required_terms,
            "min_required_matches": self.min_required_matches,
            "optional_terms": self.optional_terms,
            "negative_terms": self.negative_terms,
            "geo_focus": self.geo_focus,
            "actors": self.actors,
            "event_type": self.event_type,
            "horizon_label": self.horizon_label,
            "horizon_end": self.horizon_end,
            "min_relevance": self.min_relevance,
            "osint_queries": self.osint_queries,
        }


def _significant_terms(question: str, *, limit: int = 12) -> list[str]:
    lower = _strip_accents(question.lower())
    terms: list[str] = []
    seen: set[str] = set()

    for ent in _ENTITY_RE.findall(question):
        norm = _strip_accents(ent.lower())
        if norm not in _STOPWORDS and len(norm) >= 3 and norm not in seen:
            seen.add(norm)
            terms.append(norm)

    for tok in re.findall(r"[a-zà-ÿ]{4,}", lower):
        if tok in _STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)

    return terms[:limit]


def build_inquiry_scope(question: str, *, case_name: str = "", case_description: str = "") -> InquiryScopeProfile:
    """Build strict inquiry scope from analytical question (rule-based, no LLM)."""
    q = (question or "").strip()
    base = build_case_topic_profile(case_name or q[:80], case_description or q, q)

    required = _significant_terms(q, limit=10)
    actors = [e for e in _ENTITY_RE.findall(q) if len(e) >= 3][:6]

    geo_focus = sorted(base.primary_geos)[:6]
    negative: list[str] = []
    q_lower = _strip_accents(q.lower())
    for cluster, cluster_terms in _DISTRACTOR_CLUSTERS.items():
        cluster_in_q = any(_strip_accents(t) in q_lower for t in cluster_terms)
        if not cluster_in_q:
            negative.extend(cluster_terms[:4])

    horizon_label = ""
    horizon_end = None
    hm = _HORIZON_RE.search(q)
    if hm:
        horizon_label = hm.group(1).strip()
        if re.search(r"\d{4}", horizon_label):
            horizon_end = re.search(r"\d{4}", horizon_label).group(0)  # type: ignore[union-attr]

    min_req = 2 if len(required) >= 3 else 1
    if geo_focus and len(required) >= 2:
        min_req = min(2, max(1, len(required) // 3 + 1))

    queries: list[str] = []
    if actors and geo_focus:
        queries.append(" ".join(actors[:2] + geo_focus[:1])[:100])
    if required:
        queries.append(" ".join(required[:5])[:100])
    if actors:
        queries.append(" ".join(actors[:3])[:80])
    seen_q: set[str] = set()
    unique_queries: list[str] = []
    for qq in queries:
        key = qq.lower()
        if qq and key not in seen_q:
            seen_q.add(key)
            unique_queries.append(qq)

    event_type = "diplomatic"
    if any(t in q_lower for t in ("blockade", "bloqueig", "military", "war", "conflict", "hormuz")):
        event_type = "security_maritime"
    elif any(t in q_lower for t in ("leadership", "lideratge", "regime", "succession")):
        event_type = "political_transition"
    elif any(t in q_lower for t in ("normalize", "normalitz", "relations", "relacions", "diplomatic")):
        event_type = "bilateral_relations"

    return InquiryScopeProfile(
        question=q,
        required_terms=required,
        min_required_matches=min_req,
        optional_terms=sorted(base.keywords)[:15],
        negative_terms=negative[:20],
        geo_focus=geo_focus,
        actors=actors,
        event_type=event_type,
        horizon_label=horizon_label,
        horizon_end=horizon_end,
        base_profile=base,
        min_relevance=0.40,
        osint_queries=unique_queries[:3],
    )


def score_inquiry_relevance(
    text: str,
    title: str = "",
    *,
    inquiry: InquiryScopeProfile | None,
    min_score: float | None = None,
) -> dict[str, Any]:
    """Stricter relevance: must-match required terms + base profile score."""
    if not inquiry:
        base = score_text_relevance(text, title, profile=None)
        return {**base, "required_hits": 0, "passed_must_match": True}

    profile = inquiry.base_profile or build_case_topic_profile(inquiry.question, "", "")
    base = score_text_relevance(text, title, profile=profile)
    blob = _strip_accents(f"{title} {text}".lower())

    req_hits = _count_hits(blob, inquiry.required_terms)
    passed_must = req_hits >= inquiry.min_required_matches

    neg_hits = _count_hits(blob, inquiry.negative_terms)
    geo_hits = _count_hits(blob, inquiry.geo_focus)

    score = base["score"]
    reasons = list(base.get("reasons") or [])

    if passed_must:
        score = min(1.0, score + min(0.25, req_hits * 0.08))
        reasons.append(f"{req_hits}/{len(inquiry.required_terms)} termes obligatoris de la pregunta")
    else:
        score = min(score, 0.15)
        reasons.append(
            f"només {req_hits}/{inquiry.min_required_matches} termes obligatoris "
            f"({', '.join(inquiry.required_terms[:5])}…)"
        )

    if neg_hits >= 2 and req_hits < inquiry.min_required_matches:
        score = max(0.0, score - 0.35)
        reasons.append(f"cluster distractor detectat ({neg_hits} hits) sense focus de la pregunta")

    if inquiry.geo_focus and geo_hits == 0 and req_hits < inquiry.min_required_matches:
        score = max(0.0, score - 0.15)
        reasons.append("cap geo del focus de la pregunta")

    threshold = min_score if min_score is not None else inquiry.min_relevance
    score = max(0.0, min(1.0, round(score, 3)))

    return {
        **base,
        "score": score,
        "reasons": reasons,
        "required_hits": req_hits,
        "required_terms_needed": inquiry.min_required_matches,
        "passed_must_match": passed_must,
        "negative_hits": neg_hits,
        "passed": passed_must and score >= threshold,
        "threshold": threshold,
    }


def inquiry_scope_from_stored(data: dict[str, Any]) -> InquiryScopeProfile:
    """Rebuild scope from persisted inquiry_scope JSON."""
    q = data.get("question", "")
    scope = build_inquiry_scope(
        q,
        case_name=data.get("case_name", ""),
        case_description=data.get("case_description", ""),
    )
    if data.get("required_terms"):
        scope.required_terms = list(data["required_terms"])
    if data.get("min_required_matches") is not None:
        scope.min_required_matches = int(data["min_required_matches"])
    if data.get("osint_queries"):
        scope.osint_queries = list(data["osint_queries"])
    if data.get("min_relevance") is not None:
        scope.min_relevance = float(data["min_relevance"])
    return scope


def is_article_in_inquiry_scope(
    text: str,
    title: str = "",
    *,
    inquiry: InquiryScopeProfile | None,
    min_score: float | None = None,
) -> bool:
    return score_inquiry_relevance(text, title, inquiry=inquiry, min_score=min_score)["passed"]
