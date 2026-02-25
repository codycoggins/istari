"""Tests for MCP client — all MCP I/O is mocked, no real processes spawned."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from istari.agents.tools.base import AgentTool
from istari.tools.mcp.client import (
    MCPManager,
    MCPServerConfig,
    _result_to_str,
    load_mcp_server_configs,
    mcp_tool_to_agent_tool,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


class _TextContent:
    """Minimal TextContent-like object (type="text")."""

    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _ImageContent:
    """Non-text content — should be skipped by _result_to_str."""

    type = "image"


class _FakeTool:
    """Minimal MCP tool definition mirroring mcp.types.Tool."""

    def __init__(self, name: str, description: str, schema: dict) -> None:
        self.name = name
        self.description = description
        self.inputSchema = schema


# ── Config loading ────────────────────────────────────────────────────────────


def test_load_mcp_server_configs_empty(monkeypatch, tmp_path):
    """Missing yml returns empty list without raising."""
    monkeypatch.setattr("istari.tools.mcp.client._CONFIG_DIR", tmp_path)
    assert load_mcp_server_configs() == []


def test_load_mcp_server_configs_enabled_filter(monkeypatch, tmp_path):
    """Disabled servers are excluded; only enabled ones are returned."""
    (tmp_path / "mcp_servers.yml").write_text(
        "servers:\n"
        "  - name: active\n"
        "    command: npx\n"
        "    args: []\n"
        "    env: {}\n"
        "    enabled: true\n"
        "  - name: inactive\n"
        "    command: npx\n"
        "    args: []\n"
        "    env: {}\n"
        "    enabled: false\n"
    )
    monkeypatch.setattr("istari.tools.mcp.client._CONFIG_DIR", tmp_path)
    configs = load_mcp_server_configs()
    assert len(configs) == 1
    assert configs[0].name == "active"
    assert configs[0].enabled is True


def test_env_var_expansion(monkeypatch, tmp_path):
    """${VAR} in env values is expanded from the current process environment."""
    monkeypatch.setenv("TEST_MCP_TOKEN", "supersecret")
    (tmp_path / "mcp_servers.yml").write_text(
        "servers:\n"
        "  - name: github\n"
        "    command: npx\n"
        "    args: []\n"
        "    env:\n"
        "      GITHUB_TOKEN: ${TEST_MCP_TOKEN}\n"
        "    enabled: true\n"
    )
    monkeypatch.setattr("istari.tools.mcp.client._CONFIG_DIR", tmp_path)
    configs = load_mcp_server_configs()
    assert configs[0].env["GITHUB_TOKEN"] == "supersecret"


# ── Result conversion ─────────────────────────────────────────────────────────


def test_result_to_str_text():
    """Multiple TextContent items are joined with newlines."""
    result = MagicMock()
    result.content = [_TextContent("Hello"), _TextContent("World")]
    assert _result_to_str(result) == "Hello\nWorld"


def test_result_to_str_empty():
    """Empty content list returns the fallback string."""
    result = MagicMock()
    result.content = []
    assert _result_to_str(result) == "(no content)"


def test_result_to_str_skips_non_text():
    """Non-text content items (e.g. images) are ignored."""
    result = MagicMock()
    result.content = [_ImageContent(), _TextContent("text only")]
    assert _result_to_str(result) == "text only"


# ── Tool mapping ──────────────────────────────────────────────────────────────


def test_mcp_tool_to_agent_tool_schema():
    """Name, description, and parameters are mapped correctly from the MCP tool."""
    schema = {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}
    tool = _FakeTool("search_repos", "Search GitHub repositories", schema)
    agent_tool = mcp_tool_to_agent_tool(AsyncMock(), tool)

    assert isinstance(agent_tool, AgentTool)
    assert agent_tool.name == "search_repos"
    assert agent_tool.description == "Search GitHub repositories"
    assert agent_tool.parameters == schema


@pytest.mark.asyncio
async def test_mcp_tool_to_agent_tool_fn():
    """fn calls session.call_tool with the tool name and kwargs, returns a string."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.content = [_TextContent("found 3 repos")]
    mock_session.call_tool.return_value = mock_result

    tool = _FakeTool("search_repos", "Search repos", {"type": "object", "properties": {}})
    agent_tool = mcp_tool_to_agent_tool(mock_session, tool)

    result = await agent_tool.fn(q="istari")

    mock_session.call_tool.assert_called_once_with("search_repos", {"q": "istari"})
    assert result == "found 3 repos"


# ── MCPManager ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_manager_no_servers():
    """No configs → empty tool list, no crash."""
    async with MCPManager([]) as manager:
        tools = await manager.get_agent_tools()
    assert tools == []


@pytest.mark.asyncio
async def test_mcp_manager_get_tools(monkeypatch):
    """Connected session tools are returned as AgentTools."""
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()

    list_result = MagicMock()
    list_result.tools = [
        _FakeTool("list_repos", "List repos", {"type": "object", "properties": {}})
    ]
    mock_session.list_tools.return_value = list_result

    @asynccontextmanager
    async def mock_stdio_client(params):
        yield (MagicMock(), MagicMock())

    @asynccontextmanager
    async def mock_client_session(read, write):
        yield mock_session

    monkeypatch.setattr("istari.tools.mcp.client.stdio_client", mock_stdio_client)
    monkeypatch.setattr("istari.tools.mcp.client.ClientSession", mock_client_session)

    config = MCPServerConfig(name="github", command="npx", args=[], env={}, enabled=True)
    async with MCPManager([config]) as manager:
        tools = await manager.get_agent_tools()
        assert len(tools) == 1

    assert tools[0].name == "list_repos"
    assert isinstance(tools[0], AgentTool)
