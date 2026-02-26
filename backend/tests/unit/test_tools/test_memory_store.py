"""Tests for MemoryStore — store, list, search."""

import pytest

from istari.tools.memory.store import MemoryStore


class TestMemoryStore:
    @pytest.fixture(autouse=True)
    def mock_embedding_default(self, monkeypatch):
        """Default: embedding fails so store() saves embedding=None (SQLite-safe)."""

        async def _no_embed(text: str) -> list[float]:
            raise RuntimeError("embedding not mocked")

        monkeypatch.setattr("istari.tools.memory.store.generate_embedding", _no_embed)

    async def test_store_memory(self, db_session):
        store = MemoryStore(db_session)
        memory = await store.store("I prefer morning meetings")
        assert memory.id is not None
        assert memory.content == "I prefer morning meetings"
        assert memory.type.value == "explicit"
        assert memory.confidence == 1.0

    async def test_store_with_source(self, db_session):
        store = MemoryStore(db_session)
        memory = await store.store("Likes Python", source="observation")
        assert memory.source == "observation"

    async def test_list_explicit(self, db_session):
        store = MemoryStore(db_session)
        await store.store("Memory 1")
        await store.store("Memory 2")
        memories = await store.list_explicit()
        assert len(memories) == 2

    async def test_list_returns_newest_first(self, db_session):
        store = MemoryStore(db_session)
        await store.store("First")
        await store.store("Second")
        memories = await store.list_explicit()
        assert memories[0].content == "Second"

    async def test_search_finds_match(self, db_session):
        store = MemoryStore(db_session)
        await store.store("I prefer morning meetings")
        await store.store("I like coffee")
        results = await store.search("morning")
        assert len(results) == 1
        assert results[0].content == "I prefer morning meetings"

    async def test_search_no_match(self, db_session):
        store = MemoryStore(db_session)
        await store.store("I prefer morning meetings")
        results = await store.search("evening")
        assert len(results) == 0

    async def test_search_case_insensitive(self, db_session):
        store = MemoryStore(db_session)
        await store.store("Prefers PYTHON over JavaScript")
        results = await store.search("python")
        assert len(results) == 1

    async def test_store_calls_embedding(self, db_session, monkeypatch):
        calls: list[str] = []

        async def mock_embedding(text: str) -> list[float]:
            calls.append(text)
            raise RuntimeError("sqlite cannot store vectors")

        monkeypatch.setattr("istari.tools.memory.store.generate_embedding", mock_embedding)
        store = MemoryStore(db_session)
        memory = await store.store("I prefer dark mode")
        assert calls == ["I prefer dark mode"]
        assert memory.id is not None  # saved despite embedding failure

    async def test_store_embedding_failure_is_graceful(self, db_session, monkeypatch):
        async def mock_embedding(text: str) -> list[float]:
            raise RuntimeError("ollama down")

        monkeypatch.setattr("istari.tools.memory.store.generate_embedding", mock_embedding)
        store = MemoryStore(db_session)
        memory = await store.store("I prefer dark mode")
        assert memory.id is not None
        assert memory.embedding is None

    async def test_search_falls_back_to_ilike_on_embedding_failure(self, db_session, monkeypatch):
        async def mock_embedding(text: str) -> list[float]:
            raise RuntimeError("ollama down")

        monkeypatch.setattr("istari.tools.memory.store.generate_embedding", mock_embedding)
        store = MemoryStore(db_session)
        await store.store("I prefer morning meetings")
        results = await store.search("morning")
        assert len(results) == 1
        assert results[0].content == "I prefer morning meetings"

    async def test_search_calls_embedding_for_query(self, db_session, monkeypatch):
        calls: list[str] = []

        async def mock_embedding(text: str) -> list[float]:
            calls.append(text)
            raise RuntimeError("sqlite cannot store vectors")

        monkeypatch.setattr("istari.tools.memory.store.generate_embedding", mock_embedding)
        store = MemoryStore(db_session)
        # store() calls embedding once (fails gracefully → embedding=None)
        await store.store("I prefer morning meetings")
        # search() calls embedding once more; fails → ILIKE fallback
        results = await store.search("morning")
        assert len(calls) == 2
        assert len(results) == 1
