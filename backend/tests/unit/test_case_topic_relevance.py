"""Tests for case-topic relevance filtering."""
from services.case_topic_relevance import (
    build_case_topic_profile,
    is_article_on_topic,
    score_text_relevance,
)


def test_japan_rearmament_profile():
    profile = build_case_topic_profile(
        "Rearmament del Japó",
        "Anàlisi del rearmament japonès i la resposta de la Xina al Indo-Pacífic",
    )
    assert "japó" in profile.keywords or "japan" in profile.keywords
    assert "rearmament" in profile.themes or any("japan" in g.lower() for g in profile.primary_geos)


def test_iran_article_low_relevance_for_japan_case():
    profile = build_case_topic_profile(
        "Rearmament del Japó",
        "Rearmament japonès, JSDF, Article 9",
    )
    score = score_text_relevance(
        "Iran's IRGC warned it would set ships ablaze in the Strait of Hormuz.",
        "Iran closes Hormuz",
        profile,
    )
    assert score["score"] < 0.28
    assert not is_article_on_topic(
        "Iran's IRGC warned it would set ships ablaze in the Strait of Hormuz.",
        "Iran closes Hormuz",
        profile,
    )


def test_pope_article_low_relevance_for_japan_case():
    profile = build_case_topic_profile("Rearmament del Japó", "defensa i Indo-Pacífic")
    score = score_text_relevance(
        "War is back in vogue said Pope Leo XIV challenging militaristic policy.",
        "The Pope on war",
        profile,
    )
    assert score["score"] < 0.28


def test_japan_article_high_relevance():
    profile = build_case_topic_profile("Rearmament del Japó", "JSDF defense budget Article 9")
    text = (
        "Japan plans to double its defense budget and expand JSDF capabilities "
        "amid concerns over China's military pressure in the Indo-Pacific."
    )
    score = score_text_relevance(text, "Japan rearmament accelerates", profile)
    assert score["score"] >= 0.28
    assert is_article_on_topic(text, "Japan rearmament accelerates", profile)
