"""Tests for briefing_summary_service."""
from __future__ import annotations

import asyncio

import pytest

from services.briefing_summary_service import (
    REPORT_BRIEFING_MAX_WORDS,
    count_words,
    summarize_briefing_for_report,
)


@pytest.mark.unit
class TestBriefingSummaryService:
    def test_count_words(self):
        assert count_words("un dos tres") == 3
        assert count_words("") == 0

    def test_short_briefing_unchanged(self):
        text = "Briefing curt amb pocs punts."
        result = asyncio.run(summarize_briefing_for_report(text))
        assert result["method"] == "original"
        assert result["truncated"] is False
        assert result["text"] == text

    def test_long_briefing_truncates_without_llm(self, monkeypatch):
        monkeypatch.setattr(
            "services.llm_service.resolve_provider",
            lambda: None,
        )
        long_text = " ".join(f"para{idx}" for idx in range(400))
        result = asyncio.run(summarize_briefing_for_report(long_text))
        assert result["truncated"] is True
        assert result["method"] == "truncate"
        assert result["word_count"] <= REPORT_BRIEFING_MAX_WORDS
        assert result["original_word_count"] == 400

    def test_empty_briefing(self):
        result = asyncio.run(summarize_briefing_for_report("   "))
        assert result["method"] == "empty"
        assert result["text"] == ""
