"""Tests for parse trigger service."""
import pytest

from services.parse_trigger_service import ParseTriggerService


@pytest.mark.unit
def test_parse_hormuz_question():
    out = ParseTriggerService().parse(
        "Trump announces US blockade of Hormuz lifted by December 2026?"
    )
    assert out["ok"] is True
    assert out["llm_used"] is False
    assert "trump" in [a.lower() for a in out["actors"]] or any(
        "trump" in t for t in out["required_terms"]
    )
    assert out.get("horizon_label")


@pytest.mark.unit
def test_parse_too_short():
    out = ParseTriggerService().parse("Too short")
    assert out["ok"] is False
