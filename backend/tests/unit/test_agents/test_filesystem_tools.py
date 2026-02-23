"""Tests for filesystem agent tools (read_file, search_files)."""

import pytest

from istari.agents.tools.filesystem import make_filesystem_tools


@pytest.fixture
def tools():
    return {t.name: t for t in make_filesystem_tools()}


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFileTool:
    async def test_returns_file_contents(self, tmp_path, tools):
        f = tmp_path / "notes.md"
        f.write_text("Hello, world!\nAction item: call Bob.")

        result = await tools["read_file"].fn(path=str(f))

        assert "Hello, world!" in result
        assert "Action item: call Bob." in result

    async def test_truncates_large_file(self, tmp_path, tools):
        f = tmp_path / "big.txt"
        f.write_text("x" * 10_000)

        result = await tools["read_file"].fn(path=str(f))

        assert "truncated" in result
        assert len(result) < 10_000

    async def test_missing_file_returns_error_string(self, tmp_path, tools):
        result = await tools["read_file"].fn(path=str(tmp_path / "nope.txt"))

        assert "not found" in result.lower()

    async def test_binary_file_returns_error_string(self, tmp_path, tools):
        f = tmp_path / "img.png"
        f.write_bytes(bytes(range(256)))

        result = await tools["read_file"].fn(path=str(f))

        assert "binary" in result.lower()

    async def test_tilde_expansion(self, tools, monkeypatch, tmp_path):
        """~ should expand to tmp_path (simulated home dir)."""
        monkeypatch.setenv("HOME", str(tmp_path))
        f = tmp_path / "hi.txt"
        f.write_text("expanded!")

        result = await tools["read_file"].fn(path="~/hi.txt")

        assert "expanded!" in result

    async def test_relative_path_resolves_from_home(self, tools, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        f = tmp_path / "rel.txt"
        f.write_text("relative content")

        result = await tools["read_file"].fn(path="rel.txt")

        assert "relative content" in result


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------


class TestSearchFilesTool:
    async def test_finds_matching_file(self, tmp_path, tools):
        (tmp_path / "meeting.md").write_text("Action: @cody review PR by Friday")
        (tmp_path / "other.txt").write_text("Nothing relevant here")

        result = await tools["search_files"].fn(
            query="Action: @cody", directory=str(tmp_path)
        )

        assert "meeting.md" in result
        assert "other.txt" not in result

    async def test_no_match_returns_friendly_message(self, tmp_path, tools):
        (tmp_path / "file.txt").write_text("unrelated content")

        result = await tools["search_files"].fn(
            query="xyzzy_not_there", directory=str(tmp_path)
        )

        assert "no files" in result.lower()

    async def test_extension_filter_limits_scope(self, tmp_path, tools):
        (tmp_path / "notes.md").write_text("find me here")
        (tmp_path / "data.csv").write_text("find me here")

        result = await tools["search_files"].fn(
            query="find me here",
            directory=str(tmp_path),
            extensions="md",
        )

        assert "notes.md" in result
        assert "data.csv" not in result

    async def test_preview_line_shown(self, tmp_path, tools):
        (tmp_path / "doc.txt").write_text("irrelevant\nTODO: fix the bug\nmore text")

        result = await tools["search_files"].fn(
            query="TODO: fix", directory=str(tmp_path)
        )

        assert "TODO: fix" in result

    async def test_nonexistent_directory(self, tools):
        result = await tools["search_files"].fn(
            query="anything", directory="/nonexistent/path/xyz"
        )

        assert "no files" in result.lower()


# ---------------------------------------------------------------------------
# Schema and structure
# ---------------------------------------------------------------------------


class TestFilesystemToolSchema:
    def test_no_args_needed(self):
        tools = make_filesystem_tools()
        assert len(tools) == 2

    def test_tool_names(self):
        tools = {t.name for t in make_filesystem_tools()}
        assert "read_file" in tools
        assert "search_files" in tools

    def test_valid_openai_schemas(self):
        for tool in make_filesystem_tools():
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            fn = schema["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_read_file_requires_path(self):
        tools = {t.name: t for t in make_filesystem_tools()}
        schema = tools["read_file"].to_openai_schema()
        assert "path" in schema["function"]["parameters"]["required"]

    def test_search_files_requires_query(self):
        tools = {t.name: t for t in make_filesystem_tools()}
        schema = tools["search_files"].to_openai_schema()
        assert "query" in schema["function"]["parameters"]["required"]
