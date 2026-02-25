"""MCP client — connects to external MCP servers and exposes their tools as AgentTools.

Architecture:
  mcp_servers.yml → MCPManager (lifespan) → list[AgentTool] → app.state.mcp_tools
  → build_tools() → run_agent()

Each enabled server is spawned as a stdio subprocess; tools from all servers are
merged into the agent's tool registry. Failed connections are logged and skipped —
startup never crashes due to an unavailable MCP server.
"""

import logging
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from istari.agents.tools.base import AgentTool

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = False


def load_mcp_server_configs() -> list[MCPServerConfig]:
    """Load enabled MCP server configs from mcp_servers.yml.

    ${VAR} references in env values are expanded from the current environment.
    Disabled servers (enabled: false) are excluded from the returned list.
    Returns an empty list if the config file is missing.
    """
    path = _CONFIG_DIR / "mcp_servers.yml"
    if not path.exists():
        return []
    with open(path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    configs: list[MCPServerConfig] = []
    for srv in data.get("servers", []):
        if not srv.get("enabled", False):
            continue
        env = {k: os.path.expandvars(str(v)) for k, v in srv.get("env", {}).items()}
        configs.append(
            MCPServerConfig(
                name=srv["name"],
                command=srv["command"],
                args=srv.get("args", []),
                env=env,
                enabled=True,
            )
        )
    return configs


def _result_to_str(result: Any) -> str:
    """Convert MCP CallToolResult content to a plain string."""
    parts = [item.text for item in result.content if getattr(item, "type", None) == "text"]
    return "\n".join(parts) if parts else "(no content)"


def mcp_tool_to_agent_tool(session: Any, mcp_tool: Any) -> AgentTool:
    """Create an AgentTool that wraps an MCP tool via the given session."""
    tool_name: str = mcp_tool.name

    async def fn(**kwargs: Any) -> str:
        result = await session.call_tool(tool_name, kwargs)
        return _result_to_str(result)

    return AgentTool(
        name=tool_name,
        description=mcp_tool.description or "MCP tool",
        parameters=mcp_tool.inputSchema or {"type": "object", "properties": {}},
        fn=fn,
    )


class MCPManager:
    """Async context manager that connects to MCP servers and provides their tools.

    Usage::

        async with MCPManager(configs) as manager:
            app.state.mcp_tools = await manager.get_agent_tools()
            yield  # app runs here; MCP server processes stay alive

    Failed connections are logged as warnings and skipped — the manager never
    raises during startup.
    """

    def __init__(self, configs: list[MCPServerConfig]) -> None:
        self._configs = configs
        self._sessions: list[tuple[str, Any]] = []
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPManager":
        for config in self._configs:
            try:
                env: dict[str, str] | None = (
                    {**dict(os.environ), **config.env} if config.env else None
                )
                params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=env,
                )
                read, write = await self._exit_stack.enter_async_context(stdio_client(params))
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._sessions.append((config.name, session))
                logger.info("MCP server connected: %s", config.name)
            except Exception:
                logger.warning(
                    "MCP server failed to connect: %s", config.name, exc_info=True
                )
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._exit_stack.aclose()

    async def get_agent_tools(self) -> list[AgentTool]:
        """Return all tools from all connected MCP sessions as AgentTools."""
        tools: list[AgentTool] = []
        for name, session in self._sessions:
            try:
                result = await session.list_tools()
                for mcp_tool in result.tools:
                    tools.append(mcp_tool_to_agent_tool(session, mcp_tool))
            except Exception:
                logger.warning(
                    "Failed to list tools from MCP server: %s", name, exc_info=True
                )
        return tools
