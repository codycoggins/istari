"""Tests for build_system_prompt — SOUL.md + USER.md + memories injection."""


from istari.agents.chat import _FALLBACK_SOUL, build_system_prompt
from istari.tools.memory.store import MemoryStore


class TestBuildSystemPromptFiles:
    async def test_uses_soul_md_when_present(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are TestBot, a helpful assistant.")

        prompt = await build_system_prompt(db_session)

        assert "TestBot" in prompt
        assert _FALLBACK_SOUL not in prompt

    async def test_falls_back_to_default_when_soul_missing(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        # No SOUL.md written

        prompt = await build_system_prompt(db_session)

        assert "Istari" in prompt  # fallback mentions Istari

    async def test_injects_user_profile_when_present(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")
        (tmp_path / "USER.md").write_text("Name: Cody\nRole: Engineer")

        prompt = await build_system_prompt(db_session)

        assert "User Profile" in prompt
        assert "Cody" in prompt

    async def test_user_md_section_absent_when_file_missing(
        self, db_session, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")
        # No USER.md

        prompt = await build_system_prompt(db_session)

        assert "User Profile" not in prompt

    async def test_falls_back_to_user_name_when_no_user_md(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        prompt = await build_system_prompt(db_session, user_name="Cody")

        assert "Cody" in prompt

    async def test_user_md_takes_precedence_over_user_name(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")
        (tmp_path / "USER.md").write_text("Name: Alex")

        prompt = await build_system_prompt(db_session, user_name="Cody")

        assert "Alex" in prompt
        # user_name fallback should NOT appear since USER.md is present
        assert "The user's name is Cody" not in prompt


class TestBuildSystemPromptMemories:
    async def test_injects_stored_memories(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        store = MemoryStore(db_session)
        await store.store("User prefers dark mode", source="chat")
        await store.store("User works at Acme Corp", source="chat")
        await db_session.flush()

        prompt = await build_system_prompt(db_session)

        assert "dark mode" in prompt
        assert "Acme Corp" in prompt
        assert "What you know about this user" in prompt

    async def test_no_memory_section_when_empty(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        prompt = await build_system_prompt(db_session)

        assert "What you know about this user" not in prompt

    async def test_injection_order_soul_then_user_then_memories(
        self, db_session, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("SOUL_CONTENT")
        (tmp_path / "USER.md").write_text("USER_CONTENT")

        store = MemoryStore(db_session)
        await store.store("mem fact", source="chat")
        await db_session.flush()

        prompt = await build_system_prompt(db_session)

        soul_pos = prompt.index("SOUL_CONTENT")
        user_pos = prompt.index("USER_CONTENT")
        mem_pos = prompt.index("mem fact")
        assert soul_pos < user_pos < mem_pos

    async def test_uses_semantic_search_when_user_message_given(
        self, db_session, tmp_path, monkeypatch
    ):
        """When user_message is provided, search() is called instead of list_explicit()."""
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        search_calls: list[str] = []

        async def mock_search(self, query: str):
            search_calls.append(query)
            return []

        async def mock_list(self):
            return []

        monkeypatch.setattr("istari.tools.memory.store.MemoryStore.search", mock_search)
        monkeypatch.setattr("istari.tools.memory.store.MemoryStore.list_explicit", mock_list)

        await build_system_prompt(db_session, user_message="what are my preferences?")

        assert search_calls == ["what are my preferences?"]

    async def test_falls_back_to_list_explicit_when_search_empty(
        self, db_session, tmp_path, monkeypatch
    ):
        """When semantic search returns empty, fall back to list_explicit()."""
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        store = MemoryStore(db_session)
        await store.store("User prefers vim", source="chat")
        await db_session.flush()

        async def mock_search(self, query: str):
            return []  # semantic returns nothing → should fall back to list_explicit

        monkeypatch.setattr("istari.tools.memory.store.MemoryStore.search", mock_search)

        prompt = await build_system_prompt(
            db_session, user_message="what are my preferences?"
        )

        assert "vim" in prompt  # list_explicit fallback injected the memory

    async def test_uses_list_explicit_when_no_user_message(
        self, db_session, tmp_path, monkeypatch
    ):
        """Without user_message, list_explicit() is used (no search called)."""
        monkeypatch.setattr("istari.agents.chat._MEMORY_DIR", tmp_path)
        (tmp_path / "SOUL.md").write_text("You are Istari.")

        search_calls: list[str] = []

        async def mock_search(self, query: str):
            search_calls.append(query)
            return []

        monkeypatch.setattr("istari.tools.memory.store.MemoryStore.search", mock_search)

        store = MemoryStore(db_session)
        await store.store("User likes jazz", source="chat")
        await db_session.flush()

        prompt = await build_system_prompt(db_session)

        assert search_calls == []  # search not called without user_message
        assert "jazz" in prompt  # list_explicit used instead
