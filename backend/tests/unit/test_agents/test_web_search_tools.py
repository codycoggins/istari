"""Tests for the web_search agent tool."""

import pytest

from istari.agents.tools.web import make_web_search_tools
from istari.tools.web.searcher import SearchResult


@pytest.fixture
def tools() -> dict:
    return {t.name: t for t in make_web_search_tools()}


class TestWebSearchToolSchema:
    def test_tool_registered(self, tools: dict) -> None:
        assert "web_search" in tools

    def test_openai_schema_valid(self, tools: dict) -> None:
        schema = tools["web_search"].to_openai_schema()
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] == "web_search"
        assert "query" in fn["parameters"]["required"]
        assert "max_results" not in fn["parameters"]["required"]


class TestWebSearchTool:
    async def test_returns_formatted_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import istari.tools.web.searcher as searcher_mod

        fake_results = [
            SearchResult(
                title="Weather 20852",
                url="https://weather.example.com",
                snippet="Partly cloudy, 65°F in Rockville, MD.",
            ),
        ]

        async def mock_search(query: str, max_results: int = 5) -> list[SearchResult]:
            return fake_results

        # Patch at the source module — the closure re-imports on each call
        monkeypatch.setattr(searcher_mod, "search", mock_search)

        tools = {t.name: t for t in make_web_search_tools()}
        result = await tools["web_search"].fn(query="weather 20852", max_results=5)
        assert "Weather 20852" in result
        assert "weather.example.com" in result
        assert "Partly cloudy" in result

    async def test_no_results(
        self, tools: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import istari.tools.web.searcher as searcher_mod

        async def mock_search(query: str, max_results: int = 5) -> list[SearchResult]:
            return []

        monkeypatch.setattr(searcher_mod, "search", mock_search)
        # Patch at the agent tools level too
        import istari.agents.tools.web as web_mod

        monkeypatch.setattr(web_mod, "search", mock_search, raising=False)

        result = await tools["web_search"].fn(query="xyzzy nonexistent")
        assert "No results" in result

    async def test_search_error_returns_friendly_message(
        self, tools: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import istari.tools.web.searcher as searcher_mod

        async def mock_search(query: str, max_results: int = 5) -> list[SearchResult]:
            raise RuntimeError("network error")

        monkeypatch.setattr(searcher_mod, "search", mock_search)

        result = await tools["web_search"].fn(query="anything")
        assert "failed" in result.lower() or "moment" in result.lower()
