"""
Unified LLM provider for extraction and scenario streaming.
Supports Anthropic, OpenAI, and Google Gemini via LLM_PROVIDER or auto-detection.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Literal, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai", "gemini"]
Mode = Literal["extract", "scenario"]

_PLACEHOLDER_OPENAI = "sk-proj-TU_CLAVE_API_AQUI"


def _openai_configured() -> bool:
    key = (settings.OPENAI_API_KEY or "").strip()
    return bool(key and key != _PLACEHOLDER_OPENAI)


def _anthropic_configured() -> bool:
    return bool((settings.ANTHROPIC_API_KEY or "").strip())


def _gemini_configured() -> bool:
    return bool((settings.GEMINI_API_KEY or "").strip())


def _provider_has_key(provider: Provider) -> bool:
    if provider == "anthropic":
        return _anthropic_configured()
    if provider == "openai":
        return _openai_configured()
    return _gemini_configured()


def resolve_provider() -> Optional[Provider]:
    """Return active provider from LLM_PROVIDER or first configured key (auto)."""
    pref = (settings.LLM_PROVIDER or "auto").strip().lower()
    if pref in ("anthropic", "openai", "gemini"):
        return pref if _provider_has_key(pref) else None
    for candidate in ("anthropic", "openai", "gemini"):
        if _provider_has_key(candidate):
            return candidate
    return None


def provider_status() -> dict:
    """Return configuration status for all LLM providers and the active one."""
    active = resolve_provider()
    return {
        "provider": active,
        "configured": active is not None,
        "llm_provider_setting": (settings.LLM_PROVIDER or "auto").strip().lower(),
        "providers": {
            "anthropic": {
                "configured": _anthropic_configured(),
                "extract_model": settings.ANTHROPIC_EXTRACT_MODEL,
                "scenario_model": settings.ANTHROPIC_SCENARIO_MODEL,
            },
            "openai": {
                "configured": _openai_configured(),
                "extract_model": settings.OPENAI_EXTRACT_MODEL,
                "scenario_model": settings.OPENAI_SCENARIO_MODEL,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
            },
            "gemini": {
                "configured": _gemini_configured(),
                "extract_model": settings.GEMINI_EXTRACT_MODEL,
                "scenario_model": settings.GEMINI_SCENARIO_MODEL,
            },
        },
    }


def llm_config_error_message() -> str:
    pref = (settings.LLM_PROVIDER or "auto").strip().lower()
    if pref in ("anthropic", "openai", "gemini"):
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        return f"LLM_PROVIDER={pref} però {env_map[pref]} no està configurada al .env"
    return (
        "Cap proveïdor LLM configurat. Afegeix almenys una clau al .env: "
        "ANTHROPIC_API_KEY, OPENAI_API_KEY o GEMINI_API_KEY "
        "(o defineix LLM_PROVIDER=anthropic|openai|gemini)"
    )


def _model_for(provider: Provider, mode: Mode) -> str:
    if provider == "anthropic":
        return (
            settings.ANTHROPIC_EXTRACT_MODEL
            if mode == "extract"
            else settings.ANTHROPIC_SCENARIO_MODEL
        )
    if provider == "openai":
        return (
            settings.OPENAI_EXTRACT_MODEL if mode == "extract" else settings.OPENAI_SCENARIO_MODEL
        )
    return settings.GEMINI_EXTRACT_MODEL if mode == "extract" else settings.GEMINI_SCENARIO_MODEL


class LLMService:
    def __init__(self, mode: Mode = "extract"):
        self.mode = mode
        self.provider = resolve_provider()

    @property
    def configured(self) -> bool:
        return self.provider is not None

    @property
    def model(self) -> str:
        if not self.provider:
            return ""
        return _model_for(self.provider, self.mode)

    def resolve_model(self, prefer_model: Optional[str] = None) -> str:
        """Return the model name that would be used for a completion."""
        return self._resolve_model(prefer_model)

    def _resolve_model(self, prefer_model: Optional[str] = None) -> str:
        """Map quality tier to the best model for the active provider."""
        if prefer_model == "sonnet":
            if self.provider == "anthropic":
                return "claude-sonnet-4-20250514"
            if self.provider == "openai":
                return settings.OPENAI_SCENARIO_MODEL or "gpt-4o"
            if self.provider == "gemini":
                return settings.GEMINI_SCENARIO_MODEL or "gemini-2.0-flash"
        return self.model

    def complete(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        prefer_model: Optional[str] = None,
    ) -> str:
        if not self.provider:
            raise RuntimeError(llm_config_error_message())

        model = self._resolve_model(prefer_model)

        if self.provider == "anthropic":
            return self._complete_anthropic(user_prompt, system_prompt, max_tokens, model)
        if self.provider == "openai":
            return self._complete_openai(user_prompt, system_prompt, max_tokens, model)
        return self._complete_gemini(user_prompt, system_prompt, max_tokens, model)

    async def stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1200,
    ) -> AsyncGenerator[str, None]:
        if not self.provider:
            raise RuntimeError(llm_config_error_message())

        if self.provider == "anthropic":
            async for chunk in self._stream_anthropic(user_prompt, system_prompt, max_tokens):
                yield chunk
        elif self.provider == "openai":
            async for chunk in self._stream_openai(user_prompt, system_prompt, max_tokens):
                yield chunk
        else:
            async for chunk in self._stream_gemini(user_prompt, system_prompt, max_tokens):
                yield chunk

    def _complete_anthropic(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        model: Optional[str] = None,
    ) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        kwargs: dict = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        message = client.messages.create(**kwargs)
        return message.content[0].text

    def _complete_openai(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        model: Optional[str] = None,
    ) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        response = client.chat.completions.create(
            model=model or self.model,
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def _complete_gemini(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        model: Optional[str] = None,
    ) -> str:
        gemini_model = model or self.model
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{gemini_model}:generateContent"
        )
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, params={"key": settings.GEMINI_API_KEY}, json=body)
            resp.raise_for_status()
            data = resp.json()
        return _gemini_text_from_response(data)

    async def _stream_anthropic(
        self, user_prompt: str, system_prompt: Optional[str], max_tokens: int
    ) -> AsyncGenerator[str, None]:
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text

    async def _stream_openai(
        self, user_prompt: str, system_prompt: Optional[str], max_tokens: int
    ) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        stream = await client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def _stream_gemini(
        self, user_prompt: str, system_prompt: Optional[str], max_tokens: int
    ) -> AsyncGenerator[str, None]:
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent"
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": settings.GEMINI_API_KEY, "alt": "sse"},
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "[DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = _gemini_text_from_response(data)
                    if text:
                        yield text


def _gemini_text_from_response(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    return "".join(part.get("text", "") for part in parts if isinstance(part, dict))
