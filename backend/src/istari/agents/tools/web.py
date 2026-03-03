"""Web search agent tool."""

import logging

from .base import AgentTool

logger = logging.getLogger(__name__)


def make_web_search_tools() -> list[AgentTool]:
    """Return web search tools. No session or API key needed."""

    async def web_search(query: str, max_results: int = 5) -> str:
        from istari.tools.web.searcher import search

        logger.info("web_search | query=%r max_results=%d", query, max_results)
        try:
            results = await search(query, max_results=max_results)
        except Exception:
            logger.exception("web_search | unexpected error")
            return "Web search failed. Try again in a moment."

        if not results:
            return f'No results found for "{query}".'

        lines = [f"- [{r.title}]({r.url})\n  {r.snippet}" for r in results]
        return f"Web search results for \"{query}\":\n\n" + "\n\n".join(lines)

    return [
        AgentTool(
            name="web_search",
            description=(
                "Search the web for current information. Use for weather, news, prices, "
                "facts, or anything requiring up-to-date information not in memory."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'weather 20852 today').",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10).",
                    },
                },
                "required": ["query"],
            },
            fn=web_search,
        ),
    ]
