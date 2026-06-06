"""Tests for hybrid parse trigger guardrails."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from services.parse_trigger_service import (
    LlmParsePayload,
    ParseTriggerService,
    _semantic_overlap_check,
)


@pytest.mark.unit
def test_parse_hormuz_question_rule_based():
    out = ParseTriggerService().parse(
        "Trump announces US blockade of Hormuz lifted by December 2026?"
    )
    assert out["ok"] is True
    assert out["llm_used"] is False
    assert out.get("parse_confidence", 0) >= 0.6
    assert "trump" in [a.lower() for a in out["actors"]] or any(
        "trump" in t for t in out["required_terms"]
    )


@pytest.mark.unit
def test_parse_too_short():
    out = ParseTriggerService().parse("Too short")
    assert out["ok"] is False


@pytest.mark.unit
def test_llm_payload_validation():
    payload = LlmParsePayload.model_validate(
        {
            "actors": ["Trump", "US"],
            "regions": ["Hormuz"],
            "event_type": "maritime",
            "horizon": "December 2026",
            "keywords": ["blockade", "Hormuz", "lifted"],
            "confidence": 0.9,
            "raw_question": "test?",
        }
    )
    assert payload.event_type == "maritime"


@pytest.mark.unit
def test_llm_payload_rejects_empty_actors():
    with pytest.raises(ValidationError):
        LlmParsePayload.model_validate(
            {
                "actors": [],
                "regions": ["Hormuz"],
                "event_type": "maritime",
                "keywords": ["a", "b", "c"],
                "confidence": 0.9,
                "raw_question": "test?",
            }
        )


@pytest.mark.unit
def test_semantic_overlap_guardrail():
    assert _semantic_overlap_check(
        "Trump blockade Hormuz lifted",
        ["Trump", "blockade", "Hormuz"],
    )
    assert not _semantic_overlap_check(
        "Unrelated question about agriculture",
        ["Trump", "blockade", "Hormuz"],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parse_hybrid_llm_happy_path():
    llm_json = {
        "actors": ["Trump", "US", "Iran"],
        "regions": ["Strait of Hormuz"],
        "event_type": "maritime",
        "horizon": "December 2026",
        "keywords": ["Trump", "blockade", "Hormuz", "lifted"],
        "confidence": 0.91,
    }
    svc = ParseTriggerService()
    with patch.object(
        svc,
        "_call_llm_structured",
        new=AsyncMock(return_value=(llm_json, 120)),
    ):
        with patch("services.llm_service.resolve_provider", return_value="anthropic"):
            out = await svc.parse_hybrid(
                "Trump announces US blockade of Hormuz lifted by December 2026?"
            )
    assert out["ok"] is True
    assert out["llm_used"] is True
    assert out["parse_confidence"] >= 0.75
    assert out["methodology"] == "hybrid_llm_rule_parse"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parse_hybrid_low_confidence_fallback():
    llm_json = {
        "actors": ["Trump"],
        "regions": ["Hormuz"],
        "event_type": "maritime",
        "horizon": None,
        "keywords": ["Trump", "blockade", "Hormuz"],
        "confidence": 0.55,
    }
    svc = ParseTriggerService()
    with patch.object(
        svc,
        "_call_llm_structured",
        new=AsyncMock(return_value=(llm_json, 80)),
    ):
        with patch("services.llm_service.resolve_provider", return_value="openai"):
            out = await svc.parse_hybrid("Trump announces US blockade of Hormuz lifted by December 2026?")
    assert out["ok"] is True
    assert out["llm_used"] is False
    assert "llm_fallback_used" in out.get("guardrail_violations", [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parse_hybrid_llm_error_fallback():
    svc = ParseTriggerService()
    with patch.object(
        svc,
        "_call_llm_structured",
        new=AsyncMock(side_effect=RuntimeError("LLM down")),
    ):
        with patch("services.llm_service.resolve_provider", return_value="openai"):
            out = await svc.parse_hybrid("Trump announces US blockade of Hormuz lifted by December 2026?")
    assert out["ok"] is True
    assert out["llm_used"] is False
