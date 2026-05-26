"""Unit tests for article fetcher and enrichment helpers."""
from integrations.article_fetcher import _extract_with_bs4, is_fetchable_url


SAMPLE_HTML = """
<html><head><title>Test Article</title></head>
<body><article>
<p>Japan announced a significant increase in defense spending aimed at countering regional threats.</p>
<p>Officials in Tokyo said the move reflects growing concerns about the Indo-Pacific security environment.</p>
<p>The United States welcomed the decision as a step toward burden-sharing in the alliance.</p>
</article></body></html>
"""


def test_is_fetchable_url_skips_google_news():
    assert not is_fetchable_url("https://news.google.com/rss/articles/abc")
    assert is_fetchable_url("https://www.foreignaffairs.com/article/test")


def test_bs4_extracts_article_body():
    body = _extract_with_bs4(SAMPLE_HTML)
    assert "Japan announced" in body
    assert len(body) >= 120
