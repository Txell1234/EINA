"""Tests for curated RSS feed matching."""
from integrations.rss_feeds import match_curated_feeds


def test_match_japan_rearmament():
    feeds = match_curated_feeds("Rearmament Japó", "anàlisi de defensa i geopolítica")
    urls = [f["url"] for f in feeds]
    assert any("japantimes" in u for u in urls)


def test_match_china():
    feeds = match_curated_feeds("Relacions Xina-EUA", "BRI taiwan")
    urls = [f["url"] for f in feeds]
    assert any("substack" in u for u in urls)
