from __future__ import annotations

import asyncio
import time
from typing import Any

from ...tools.registry import register_mcp_tools
from ...types.mcp import McpServerConnection, PendingMcpServer, ScopedMcpServerConfig
from ...utils.log import debug_log
from .client import clear_server_cache, connect_mcp_server
from .config import load_mcp_configs
from .fetch_tools import fetch_tools_for_connection
from .registry import (
    clear_mcp_registry,
    delete_mcp_registry_entry,
    get_mcp_registry,
    get_mcp_registry_entry,
    set_mcp_registry_entry,
)


class McpBootstrapResult:
    def __init__(
        self,
        connections: list[McpServerConnection],
        tool_count: int,
        config_errors: list[str],
    ) -> None:
        self.connections = connections
        self.tool_count = tool_count
        self.config_errors = config_errors


async def bootstrap_mcp(cwd: str) -> McpBootstrapResult:
    config_result = load_mcp_configs(cwd)
    servers = config_result.servers
    config_errors = config_result.errors
    clear_mcp_registry()

    started_at = time.time()
    for name, config in servers.items():
        placeholder = PendingMcpServer(
            name=name,
            type="pending",
            config=config,
            started_at=started_at,
        )
        set_mcp_registry_entry(name, placeholder, [])
    _refresh_global_tool_registry()

    tasks = [
        _connect_and_register(name, config)
        for name, config in servers.items()
    ]
    settled = await asyncio.gather(*tasks, return_exceptions=True)

    connections: list[McpServerConnection] = []
    tool_count = 0
    server_names = list(servers.keys())
    for i, result in enumerate(settled):
        server_name = server_names[i]
        if isinstance(result, Exception):
            entry = get_mcp_registry_entry(server_name)
            if entry:
                connections.append(entry["connection"])
        else:
            connections.append(result["connection"])
            tool_count += result["tool_count"]

    return McpBootstrapResult(
        connections=connections,
        tool_count=tool_count,
        config_errors=config_errors,
    )


async def _connect_and_register(
    name: str,
    config: ScopedMcpServerConfig,
) -> dict[str, Any]:
    connection = await connect_mcp_server(name, config)
    tools: list[Any] = []
    if getattr(connection, "type", None) == "connected":
        try:
            tools = await fetch_tools_for_connection(connection)
        except Exception as exc:
            debug_log("mcp", f"[{name}] tools/list failed after connect: {exc}")

    set_mcp_registry_entry(name, connection, tools)
    _refresh_global_tool_registry()
    return {"connection": connection, "tool_count": len(tools)}


def _refresh_global_tool_registry() -> None:
    all_tools = []
    for entry in get_mcp_registry():
        all_tools.extend(entry["tools"])
    register_mcp_tools(all_tools)


async def reconnect_mcp_server(name: str) -> McpServerConnection | None:
    entry = get_mcp_registry_entry(name)
    if not entry:
        return None

    await clear_server_cache(name, entry["connection"].config)
    delete_mcp_registry_entry(name)
    _refresh_global_tool_registry()

    connection = await connect_mcp_server(name, entry["connection"].config)
    tools = []
    if getattr(connection, "type", None) == "connected":
        tools = await fetch_tools_for_connection(connection)

    set_mcp_registry_entry(name, connection, tools)
    _refresh_global_tool_registry()
    return connection
