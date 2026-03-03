"""Web search tool — DuckDuckGo-backed, no API key required."""

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


async def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search the web via DuckDuckGo and return structured results."""
    return await asyncio.to_thread(_search_sync, query, max_results)


def _search_sync(query: str, max_results: int) -> list[SearchResult]:
    from duckduckgo_search import DDGS

    logger.info("WebSearcher: query=%r max_results=%d", query, max_results)
    results: list[SearchResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                )
            )
    logger.info("WebSearcher: returned %d result(s)", len(results))
    return results
