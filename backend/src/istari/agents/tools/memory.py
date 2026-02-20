"""Memory agent tools — store and search the user's explicit memory."""

from sqlalchemy.ext.asyncio import AsyncSession

from istari.tools.memory.store import MemoryStore

from .base import AgentContext, AgentTool


def make_memory_tools(session: AsyncSession, context: AgentContext) -> list[AgentTool]:
    """Return memory tools bound to the given session and context."""

    async def remember(fact: str) -> str:
        store = MemoryStore(session)
        await store.store(content=fact, source="chat")
        await session.commit()
        context.memory_created = True
        return f'Remembered: "{fact}"'

    async def search_memory(query: str) -> str:
        store = MemoryStore(session)
        memories = await store.search(query)
        if not memories:
            return f'No memories found matching "{query}".'
        lines = [f"- {m.content}" for m in memories]
        return "Found memories:\n" + "\n".join(lines)

    return [
        AgentTool(
            name="remember",
            description=(
                "Store a fact or preference the user wants remembered. "
                "Use when the user says 'remember that', 'note that', or shares "
                "personal context they want saved."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The fact or preference to remember.",
                    }
                },
                "required": ["fact"],
            },
            fn=remember,
        ),
        AgentTool(
            name="search_memory",
            description="Search the user's stored memories by keyword.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for in memories.",
                    }
                },
                "required": ["query"],
            },
            fn=search_memory,
        ),
    ]
