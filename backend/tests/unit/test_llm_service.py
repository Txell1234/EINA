"""
Unit tests for multi-provider LLM configuration.
"""
import pytest

from services import llm_service as ls


@pytest.mark.unit
def test_resolve_provider_openai_only(monkeypatch):
    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "sk-real-key")
    monkeypatch.setattr(ls.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "")
    assert ls.resolve_provider() == "openai"


@pytest.mark.unit
def test_resolve_provider_gemini_only(monkeypatch):
    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(ls.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "AIza-test")
    assert ls.resolve_provider() == "gemini"


@pytest.mark.unit
def test_resolve_provider_auto_prefers_first_configured(monkeypatch):
    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "sk-real-key")
    monkeypatch.setattr(ls.settings, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "AIza-test")
    assert ls.resolve_provider() == "anthropic"


@pytest.mark.unit
def test_resolve_model_sonnet_maps_per_provider(monkeypatch):
    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "sk-real-key")
    monkeypatch.setattr(ls.settings, "OPENAI_SCENARIO_MODEL", "gpt-4o")
    monkeypatch.setattr(ls.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "")
    svc = ls.LLMService()
    assert svc.resolve_model("sonnet") == "gpt-4o"

    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "AIza-test")
    monkeypatch.setattr(ls.settings, "GEMINI_SCENARIO_MODEL", "gemini-2.0-flash")
    svc = ls.LLMService()
    assert svc.resolve_model("sonnet") == "gemini-2.0-flash"


@pytest.mark.unit
def test_provider_status_lists_all_providers(monkeypatch):
    monkeypatch.setattr(ls.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(ls.settings, "GEMINI_API_KEY", "AIza-test")
    monkeypatch.setattr(ls.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(ls.settings, "ANTHROPIC_API_KEY", "")
    status = ls.provider_status()
    assert status["provider"] == "gemini"
    assert status["configured"] is True
    assert status["providers"]["gemini"]["configured"] is True
    assert status["providers"]["openai"]["configured"] is False
