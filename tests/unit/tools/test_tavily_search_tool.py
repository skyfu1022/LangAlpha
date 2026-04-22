from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_web_search_gracefully_degrades_without_api_key(monkeypatch, caplog):
    import src.tools.search_services.tavily.tavily_search_tool as mod

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    mod._api_wrapper = None

    with caplog.at_level("WARNING"):
        content, artifact = await mod.web_search.coroutine("latest market news")

    assert isinstance(content, str)
    assert "temporarily unavailable" in content
    assert artifact["error"] == "search_unavailable"
    assert artifact["provider"] == "tavily"
    assert "Tavily search unavailable" in caplog.text


@pytest.mark.asyncio
async def test_web_search_logs_runtime_failures_once_as_warning(monkeypatch, caplog):
    import src.tools.search_services.tavily.tavily_search_tool as mod

    class BoomWrapper:
        async def raw_results(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    mod._api_wrapper = BoomWrapper()

    with caplog.at_level("WARNING"):
        content, artifact = await mod.web_search.coroutine("latest market news")

    assert "boom" in content
    assert artifact["error"] == "boom"
    assert "Tavily search failed" in caplog.text
