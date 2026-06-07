"""Condense case briefings for report output while analysis keeps the full text."""
from __future__ import annotations

import logging
import re
from typing import Any

from services.report_i18n import normalize_lang

logger = logging.getLogger(__name__)

REPORT_BRIEFING_MAX_WORDS = 300


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", (text or "").strip()))


def _truncate_to_words(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text.strip())
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words])


async def summarize_briefing_for_report(
    text: str,
    *,
    max_words: int = REPORT_BRIEFING_MAX_WORDS,
    lang: str | None = None,
) -> dict[str, Any]:
    """
    Return briefing text suitable for report export.
    Full briefing remains in the case record for analysis pipelines.
    """
    original = (text or "").strip()
    original_word_count = count_words(original)
    lang_code = normalize_lang(lang)

    if not original:
        return {
            "text": "",
            "word_count": 0,
            "original_word_count": 0,
            "truncated": False,
            "max_words": max_words,
            "method": "empty",
        }

    if original_word_count <= max_words:
        return {
            "text": original,
            "word_count": original_word_count,
            "original_word_count": original_word_count,
            "truncated": False,
            "max_words": max_words,
            "method": "original",
        }

    from services.llm_service import LLMService, resolve_provider

    if resolve_provider():
        llm = LLMService(mode="extract")
        system = (
            "Ets un analista d'intel·ligència. Condensa briefings per a informes executius. "
            "Has de conservar TOTS els punts, actors, dates, hipòtesis, riscos i dades del briefing "
            "original sense inventar res nou. "
            f"Escriu com a màxim {max_words} paraules. "
            "Respon únicament amb el text del resum, sense títols, llistes markdown ni comentaris."
        )
        user = (
            f"Idioma de sortida: {lang_code}.\n\n"
            f"Briefing original ({original_word_count} paraules):\n\n{original}"
        )
        try:
            summary = (await llm.acomplete(user, system_prompt=system, max_tokens=1400)).strip()
            summary_words = count_words(summary)
            if summary and summary_words <= max_words + 15:
                return {
                    "text": summary,
                    "word_count": summary_words,
                    "original_word_count": original_word_count,
                    "truncated": True,
                    "max_words": max_words,
                    "method": "llm",
                }
            if summary:
                trimmed = _truncate_to_words(summary, max_words)
                return {
                    "text": trimmed,
                    "word_count": count_words(trimmed),
                    "original_word_count": original_word_count,
                    "truncated": True,
                    "max_words": max_words,
                    "method": "llm_trimmed",
                }
        except Exception as exc:
            logger.warning("LLM briefing summary failed: %s", exc)

    fallback = _truncate_to_words(original, max_words)
    return {
        "text": fallback,
        "word_count": count_words(fallback),
        "original_word_count": original_word_count,
        "truncated": True,
        "max_words": max_words,
        "method": "truncate",
    }
