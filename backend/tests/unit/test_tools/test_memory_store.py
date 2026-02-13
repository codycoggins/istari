"""Tests for MemoryStore — store, list, search."""

from istari.tools.memory.store import MemoryStore


class TestMemoryStore:
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
