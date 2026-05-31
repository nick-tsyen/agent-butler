from __future__ import annotations

from typing import Any

from ...types.mcp import McpServerConnection

_entries: dict[str, dict[str, Any]] = {}


def set_mcp_registry_entry(
    name: str,
    connection: McpServerConnection,
    tools: list[Any],
) -> None:
    _entries[name] = {"connection": connection, "tools": list(tools)}


def delete_mcp_registry_entry(name: str) -> None:
    _entries.pop(name, None)


def get_mcp_registry() -> list[dict[str, Any]]:
    return [
        {"connection": e["connection"], "tools": e["tools"]}
        for e in _entries.values()
    ]


def get_mcp_registry_entry(name: str) -> dict[str, Any] | None:
    return _entries.get(name)


def get_mcp_server(name: str) -> McpServerConnection | None:
    entry = _entries.get(name)
    return entry["connection"] if entry else None


def get_all_mcp_servers() -> list[McpServerConnection]:
    return [e["connection"] for e in _entries.values()]


def set_mcp_server(name: str, connection: McpServerConnection) -> None:
    existing = _entries.get(name)
    tools = existing["tools"] if existing else []
    _entries[name] = {"connection": connection, "tools": tools}


def clear_mcp_registry() -> None:
    _entries.clear()
