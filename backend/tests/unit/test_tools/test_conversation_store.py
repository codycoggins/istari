"""Tests for ConversationStore — persist and load chat history."""


from istari.tools.conversation.store import _HISTORY_LIMIT, ConversationStore


class TestConversationStore:
    async def test_load_history_empty(self, db_session):
        history = await ConversationStore(db_session).load_history()
        assert history == []

    async def test_save_and_load_single_turn(self, db_session):
        store = ConversationStore(db_session)
        await store.save_turn("Hello", "Hi there!")
        await db_session.flush()

        history = await store.load_history()

        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}

    async def test_history_is_chronological(self, db_session):
        store = ConversationStore(db_session)
        await store.save_turn("First", "Reply 1")
        await db_session.flush()
        await store.save_turn("Second", "Reply 2")
        await db_session.flush()

        history = await store.load_history()

        assert history[0]["content"] == "First"
        assert history[1]["content"] == "Reply 1"
        assert history[2]["content"] == "Second"
        assert history[3]["content"] == "Reply 2"

    async def test_load_respects_history_limit(self, db_session):
        store = ConversationStore(db_session)
        # Insert more turns than the limit
        turns = _HISTORY_LIMIT // 2 + 5
        for i in range(turns):
            await store.save_turn(f"msg {i}", f"reply {i}")
        await db_session.flush()

        history = await store.load_history()

        assert len(history) == _HISTORY_LIMIT

    async def test_load_returns_most_recent_when_over_limit(self, db_session):
        store = ConversationStore(db_session)
        turns = _HISTORY_LIMIT // 2 + 5
        for i in range(turns):
            await store.save_turn(f"msg {i}", f"reply {i}")
        await db_session.flush()

        history = await store.load_history()

        # The most recent message should be the last assistant reply
        assert history[-1]["content"] == f"reply {turns - 1}"

    async def test_roles_are_correct(self, db_session):
        store = ConversationStore(db_session)
        await store.save_turn("user says this", "assistant says that")
        await db_session.flush()

        history = await store.load_history()

        roles = [m["role"] for m in history]
        assert roles == ["user", "assistant"]
