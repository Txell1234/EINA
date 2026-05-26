"""Tests for GDELT GFG parser and search helpers."""
import gzip
import io

import pytest

from integrations.gdelt_gfg import (
    _parse_gfg_line,
    _query_terms,
    _row_to_article,
    _scan_gfg_gzip,
)


@pytest.mark.unit
def test_parse_gfg_line_valid():
    line = (
        "20260519120000\thttps://www.reuters.com/\t5\t12.5\t"
        "https://www.reuters.com/world/taiwan-chip\tTaiwan chip exports surge…"
    )
    row = _parse_gfg_line(line)
    assert row is not None
    assert row["url"] == "https://www.reuters.com/world/taiwan-chip"
    assert row["link_percent_max_id"] == 12.5


@pytest.mark.unit
def test_row_to_article_prominence():
    article = _row_to_article(
        {
            "date": "20260519120000",
            "from_frontpage_url": "https://asia.nikkei.com/",
            "link_percent_max_id": 10.0,
            "url": "https://asia.nikkei.com/Politics/test",
            "link_text": "Japan defense budget",
        }
    )
    assert article["frontpage_score"] == 90.0
    assert article["source"] == "asia.nikkei.com"


@pytest.mark.unit
def test_scan_gfg_gzip_filters_and_sorts():
    rows = [
        "20260519120000\thttps://a.com/\t1\t5.0\thttps://a.com/taiwan\tTaiwan headline",
        "20260519120000\thttps://b.com/\t2\t80.0\thttps://b.com/other\tOther story",
        "20260519120000\thttps://c.com/\t3\t20.0\thttps://c.com/taiwan-trade\tTaiwan trade deal",
    ]
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write("\n".join(rows).encode("utf-8"))
    gz_bytes = buf.getvalue()

    articles, scanned = _scan_gfg_gzip(gz_bytes, ["taiwan"], "", max_results=5)
    assert scanned == 3
    assert len(articles) == 2
    assert articles[0]["frontpage_score"] >= articles[1]["frontpage_score"]


@pytest.mark.unit
def test_query_terms_short():
    terms = _query_terms("Taiwan semiconductor Japan")
    assert "taiwan" in terms or "Taiwan" in terms or any("taiwan" in t for t in terms)
