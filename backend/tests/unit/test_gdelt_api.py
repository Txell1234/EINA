"""Tests for GDELT API throttling and fallback."""
import pytest

from integrations.gdelt_api import _is_rate_limited, GDELTAPIService


@pytest.mark.unit
def test_is_rate_limited_detects_429_body():
    assert _is_rate_limited(429, "") is True
    assert _is_rate_limited(
        200,
        "Please limit requests to one every 5 seconds",
    ) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gdelt_falls_back_to_google_news_on_rate_limit(monkeypatch):
    svc = GDELTAPIService()
    calls = {"gdelt": 0}

    async def fake_fetch_gdelt(*args, **kwargs):
        calls["gdelt"] += 1
        return {
            "status": "error",
            "count": 0,
            "articles": [],
        }

    async def fake_google(query, max_results):
        return {
            "status": "success",
            "count": 1,
            "articles": [
                {
                    "title": "Test article",
                    "url": "https://example.com/a",
                    "date": "2026-05-01",
                    "source": "Google News",
                    "language": "",
                    "tone": "",
                }
            ],
            "provider": "google_news_rss",
            "fallback": True,
        }

    async def fake_throttle():
        return None

    monkeypatch.setattr("integrations.gdelt_api._throttle", fake_throttle)
    monkeypatch.setattr(
        "integrations.gdelt_api._fetch_google_news_fallback",
        fake_google,
    )

    async def always_rate_limited(*args, **kwargs):
        calls["gdelt"] += 1
        raise AssertionError("should use fallback path")

    # Force _fetch inner loop to break immediately
    import integrations.gdelt_api as gdelt_mod

    original_lock = gdelt_mod._request_lock

    class FakeLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(gdelt_mod, "_request_lock", FakeLock())

    async def fake_get(*args, **kwargs):
        class Resp:
            status_code = 429
            text = "Please limit requests to one every 5 seconds"

            def raise_for_status(self):
                pass

            def json(self):
                return {}

        return Resp()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            return await fake_get()

    monkeypatch.setattr(gdelt_mod.httpx, "AsyncClient", lambda **kw: FakeClient())
    monkeypatch.setattr(gdelt_mod, "_get_cached", lambda key: None)
    monkeypatch.setattr(gdelt_mod, "_set_cache", lambda key, payload: None)

    result = await svc._fetch("japan china", 7, 5)
    assert result["status"] == "success"
    assert result.get("fallback") is True
    assert result["count"] == 1
