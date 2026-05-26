"""
Validation utilities for extracted statements.
Adapted from: https://github.com/pranaykotas/china-us-rhetoric (validate.py, cleanup.py)
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from models.extract import ExtractedStatement

GROUNDING_STOPWORDS = frozenset(
    """
    the a an and or but in on at to for of with by from that this is are was were
    has have had will would should could may might not also its their our his her
    we us as it be been being said says must all any about into than more such
    when which there they what who how can do does did el la los las un una de en
    que es son fue per amb els les i o ser estar ha han
    """.split()
)

# Senyals internacionals — coded language inclòs (Occident, hegemonia, etc.)
INTL_SIGNALS = re.compile(
    r"\b("
    r"united states|u\.s\.|usa|america[hn]?|trump|biden|washington|pentagon|"
    r"nato|g7|g20|quad|aukus|five eyes|"
    r"taiwan|hong kong|south china sea|"
    r"tariff|sanction|decoupl|tech.?war|export.?control|"
    r"japan|japanese|jap[oó]n|korea|india|russia|europe|european|uk|britain|"
    r"france|germany|spain|china|chinese|xina|"
    r"united nations|un security council|wto|imf|"
    r"foreign minister|ambassador|bilateral|multilateral|diplomatic|diplomacy|"
    r"sovereignty|territorial|hegemon|imperialism|cold war|containment|"
    r"indo.?pacific|belt and road|bri|rearmament|rearmer|defense budget|"
    r"occident|occidental|western|hegemon|hegemony|alliance|sanctions|"
    r"pot[eêèé]ncies occidentals|bloc occidental|pot[eê]ncia occidental"
    r")\b",
    re.IGNORECASE,
)

DOMESTIC_SIGNALS = re.compile(
    r"\b("
    r"anti.?corruption|party congress|plenum|politburo|"
    r"five.?year plan|common prosperity|poverty alleviation|"
    r"provincial|prefecture|municipal|local election|"
    r"pension|pensions|social security|healthcare reform|education reform|"
    r"carbon neutral|ecological|green development|"
    r"pressupostos generals|pol[ií]tica interior|eleccions locals"
    r")\b",
    re.IGNORECASE,
)

GROUNDING_THRESHOLD = 0.10
GROUNDING_REVIEW_THRESHOLD = 0.08
MIN_VERIFIABLE_EXCERPT_LEN = 40


def is_verifiable_source(source_url: str | None, source_text_excerpt: str | None) -> bool:
    """True when the statement can be traced to an external document."""
    url = (source_url or "").strip()
    if not url or url.startswith("direct-analysis:"):
        return False
    excerpt = (source_text_excerpt or "").strip()
    return len(excerpt) >= MIN_VERIFIABLE_EXCERPT_LEN


def effective_grounding_score(
    statement: str,
    source_text_excerpt: str | None,
    stored_score: float | None = None,
) -> float | None:
    """
    Grounding against the original source text only.
    Returns None when there is no verifiable excerpt (never self-compare statement).
    """
    excerpt = (source_text_excerpt or "").strip()
    if len(excerpt) < MIN_VERIFIABLE_EXCERPT_LEN:
        return None
    if stored_score is not None and stored_score >= 0:
        return float(stored_score)
    return grounding_score(statement, excerpt)


def tokenize_for_grounding(text: str) -> set[str]:
    words = re.findall(r"[a-zà-ÿ]{4,}", text.lower())
    return {w for w in words if w not in GROUNDING_STOPWORDS}


def grounding_score(statement: str, source_text: str) -> float:
    """
    Fraction of significant words in the statement found in source text.
    Paraphrases score lower than direct quotes — expected.
    """
    q_words = tokenize_for_grounding(statement)
    if not q_words:
        return 1.0
    a_words = tokenize_for_grounding(source_text)
    return len(q_words & a_words) / len(q_words)


def has_international_signal(*texts: str) -> bool:
    combined = " ".join(t for t in texts if t)
    return bool(INTL_SIGNALS.search(combined))


def has_domestic_signal(*texts: str) -> bool:
    combined = " ".join(t for t in texts if t)
    return bool(DOMESTIC_SIGNALS.search(combined))


def needs_llm_cleanup(stmt: ExtractedStatement) -> bool:
    """Only ambiguous statements (no clear intl signal) need LLM classification."""
    if stmt.relevance_signals and len(stmt.relevance_signals) >= 2:
        return False
    if has_international_signal(
        stmt.statement, stmt.context, stmt.topic, stmt.source_text_excerpt or ""
    ):
        return False
    return True


def validate_statements(stmts: list[ExtractedStatement]) -> dict[str, Any]:
    """Coverage, grounding and leakage metrics for a case (china-us-rhetoric validate.py)."""
    if not stmts:
        return {
            "total_statements": 0,
            "has_data": False,
            "message": "Cap declaració extreta",
        }

    scores: list[float] = []
    unverified: list[dict[str, Any]] = []
    flagged_grounding: list[dict[str, Any]] = []
    flagged_leakage: list[dict[str, Any]] = []
    tone_counts: Counter = Counter()
    topic_counts: Counter = Counter()

    for s in stmts:
        verified = is_verifiable_source(s.source_url, s.source_text_excerpt)
        score = effective_grounding_score(s.statement, s.source_text_excerpt, s.grounding_score)
        if score is not None:
            scores.append(score)
        elif not verified:
            unverified.append(
                {
                    "id": s.id,
                    "actor": s.actor,
                    "statement": (s.statement or "")[:120],
                    "source_url": s.source_url,
                }
            )

        if verified and score is not None and score < GROUNDING_THRESHOLD:
            flagged_grounding.append(
                {
                    "id": s.id,
                    "score": round(score, 3),
                    "actor": s.actor,
                    "statement": (s.statement or "")[:120],
                    "source_url": s.source_url,
                }
            )

        intl = has_international_signal(
            s.statement, s.context, s.topic, s.source_text_excerpt or ""
        )
        domestic = has_domestic_signal(
            s.statement, s.context, s.topic, s.source_text_excerpt or ""
        )
        if not intl:
            flagged_leakage.append(
                {
                    "id": s.id,
                    "has_domestic_signal": domestic,
                    "actor": s.actor,
                    "topic": s.topic,
                    "statement": (s.statement or "")[:150],
                }
            )

        tone_counts[s.tone or "unknown"] += 1
        topic_counts[s.topic or "unknown"] += 1

    avg = sum(scores) / len(scores) if scores else 0.0
    return {
        "has_data": True,
        "total_statements": len(stmts),
        "avg_grounding": round(avg, 3),
        "above_50pct_overlap": sum(1 for x in scores if x >= 0.50),
        "above_25pct_overlap": sum(1 for x in scores if x >= 0.25),
        "below_threshold": len(flagged_grounding),
        "unverified_count": len(unverified),
        "unverified": unverified[:20],
        "grounding_threshold": GROUNDING_THRESHOLD,
        "no_intl_signal": len(flagged_leakage),
        "domestic_signal_risk": sum(1 for f in flagged_leakage if f["has_domestic_signal"]),
        "tone_distribution": dict(tone_counts.most_common()),
        "top_topics": [{"topic": t, "count": c} for t, c in topic_counts.most_common(15)],
        "flagged_grounding": flagged_grounding[:20],
        "flagged_leakage": flagged_leakage[:20],
    }
