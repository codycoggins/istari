"""Conversation store — persist and load chat history across WebSocket reconnects."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from istari.models.conversation import ConversationMessage

_HISTORY_LIMIT = 40


class ConversationStore:
    """Load and save conversation turns to the DB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_history(self) -> list[dict[str, str]]:
        """Return the most recent turns in chronological order."""
        stmt = (
            select(ConversationMessage)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(_HISTORY_LIMIT)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]

    async def save_turn(self, user_content: str, assistant_content: str) -> None:
        """Persist a user + assistant exchange."""
        self.session.add(ConversationMessage(role="user", content=user_content))
        self.session.add(ConversationMessage(role="assistant", content=assistant_content))
        await self.session.flush()
