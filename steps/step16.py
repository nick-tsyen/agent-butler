"""
Step 16 - MCP client integration

Goal:
- load MCP server configs from settings.json
- connect to stdio / http / sse servers
- fetch tools/list from each server
- wrap MCP tools as local Tool objects
- keep a small in-memory registry for /mcp

This file is a teaching version that condenses the core mechanics.
"""

from __future__ import annotations

import json
import re
from typing import Any

# ── Config validation ─────────────────────────────────────────────────────────


def validate_server_config(
    name: str, raw: Any, scope: str
) -> dict[str, Any]:
    """
    Validate an MCP server config dict.

    Returns ``{"ok": True, "value": <config>}`` on success or
    ``{"ok": False, "error": <message>}`` on failure.
    """
    if not isinstance(raw, dict):
        return {"ok": False, "error": f"mcpServers.{name} must be an object"}

    transport_type = raw.get("type")
    if transport_type is not None and transport_type not in ("stdio", "http", "sse"):
        return {
            "ok": False,
            "error": (
                f"mcpServers.{name} ({scope}): unsupported transport "
                f"'{transport_type}'. Use stdio, http, or sse."
            ),
        }

    if transport_type in ("http", "sse"):
        url = raw.get("url", "")
        if not isinstance(url, str) or not url.strip():
            return {"ok": False, "error": f"mcpServers.{name} ({scope}): url is required"}
        return {
            "ok": True,
            "value": {
                "type": transport_type,
                "url": url,
                "headers": raw.get("headers"),
            },
        }

    # Default to stdio
    command = raw.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return {"ok": False, "error": f"mcpServers.{name} ({scope}): command is required"}

    return {
        "ok": True,
        "value": {
            "type": "stdio",
            "command": command,
            "args": raw.get("args", []) if isinstance(raw.get("args"), list) else [],
            "env": raw.get("env"),
        },
    }


# ── Name normalization ────────────────────────────────────────────────────────


def normalize_name_for_mcp(name: str) -> str:
    """Replace any character that is not alphanumeric, underscore, or dash with '_'."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(name))


def build_mcp_tool_name(server_name: str, tool_name: str) -> str:
    """Build the fully-qualified MCP tool name ``mcp__<server>__<tool>``."""
    return f"mcp__{normalize_name_for_mcp(server_name)}__{normalize_name_for_mcp(tool_name)}"


def parse_mcp_tool_name(full_name: str) -> dict[str, str] | None:
    """
    Parse a fully-qualified MCP tool name back into server and tool components.

    Returns None if *full_name* does not match the expected pattern.
    """
    parts = str(full_name).split("__")
    if len(parts) < 3 or parts[0] != "mcp" or not parts[1]:
        return None
    return {
        "server_name": parts[1],
        "tool_name": "__".join(parts[2:]),
    }


# ── Small MCP registry ────────────────────────────────────────────────────────

# Maps server_name → {"connection": …, "tools": […]}
_registry_entries: dict[str, dict[str, Any]] = {}


def set_mcp_registry_entry(
    name: str, connection: Any, tools: list[Any]
) -> None:
    """Register (or replace) a server entry in the in-memory registry."""
    _registry_entries[name] = {"connection": connection, "tools": tools}


def get_mcp_registry() -> list[dict[str, Any]]:
    """Return all registry entries as a list."""
    return list(_registry_entries.values())


def get_mcp_registry_entry(name: str) -> dict[str, Any] | None:
    """Return the registry entry for *name*, or None."""
    return _registry_entries.get(name)


def clear_mcp_registry() -> None:
    """Remove all entries from the registry."""
    _registry_entries.clear()


# ── Transport factories (teaching stubs) ──────────────────────────────────────


def create_stdio_transport(config: dict[str, Any]) -> dict[str, Any]:
    """Return a teaching stub for a stdio transport."""
    return {
        "kind": "stdio",
        "describe": f"stdio: {config['command']} {' '.join(config.get('args', []))}",
        "transport": {
            "type": "stdio",
            "command": config["command"],
            "args": config.get("args", []),
            "env": config.get("env", {}),
        },
        "collect_stderr_tail": lambda: "",
        "pre_cleanup": lambda: None,
    }


def create_http_transport(config: dict[str, Any]) -> dict[str, Any]:
    """Return a teaching stub for an HTTP transport."""
    return {
        "kind": "http",
        "describe": f"http: {config['url']}",
        "transport": {
            "type": "http",
            "url": config["url"],
            "headers": {
                "User-Agent": "agent-butler/0.1.0",
                **(config.get("headers") or {}),
            },
        },
        "collect_stderr_tail": lambda: "",
        "pre_cleanup": lambda: None,
    }


def create_sse_transport(config: dict[str, Any]) -> dict[str, Any]:
    """Return a teaching stub for an SSE transport."""
    headers = {
        "User-Agent": "agent-butler/0.1.0",
        **(config.get("headers") or {}),
    }
    return {
        "kind": "sse",
        "describe": f"sse: {config['url']}",
        "transport": {
            "type": "sse",
            "url": config["url"],
            "request_headers": headers,
            "event_source_headers": {**headers, "Accept": "text/event-stream"},
        },
        "collect_stderr_tail": lambda: "",
        "pre_cleanup": lambda: None,
    }


def create_transport_bundle(config: dict[str, Any]) -> dict[str, Any]:
    """Choose and create the appropriate transport based on ``config['type']``."""
    if config.get("type") == "http":
        return create_http_transport(config)
    if config.get("type") == "sse":
        return create_sse_transport(config)
    return create_stdio_transport(config)


# ── Connection cache + connect flow ───────────────────────────────────────────

# Cache: cache_key → connection dict (or pending coroutine stub).
_connection_cache: dict[str, Any] = {}


def _get_cache_key(name: str, config: dict[str, Any]) -> str:
    return f"{name}:{json.dumps(config, sort_keys=True)}"


async def connect_to_server(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    Connect to an MCP server, caching the connection by name+config.

    Returns a connection dict.  In production this is where the MCP SDK
    Client connects via the transport; here we return a teaching stub.
    """
    cache_key = _get_cache_key(name, config)
    if cache_key in _connection_cache:
        return _connection_cache[cache_key]

    connection = await _do_connect(name, config)
    _connection_cache[cache_key] = connection
    return connection


async def _do_connect(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Perform the actual connection (teaching stub)."""
    _bundle = create_transport_bundle(config)

    # In the real implementation the MCP SDK Client connects here.
    # We return a stub that responds to tools/list and tools/call.
    async def _request(payload: dict[str, Any]) -> dict[str, Any]:
        method = payload.get("method")

        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo back the provided message.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"],
                        },
                        "annotations": {"readOnlyHint": True},
                    }
                ]
            }

        if method == "tools/call":
            args = payload.get("params", {}).get("arguments", {})
            return {
                "content": [{"type": "text", "text": str(args.get("message", ""))}],
                "isError": False,
            }

        raise RuntimeError(f"Unsupported MCP request: {method}")

    return {
        "name": name,
        "type": "connected",
        "config": config,
        "capabilities": {"tools": {}},
        "server_info": {"name": name, "version": "0.0.0"},
        "client": {"request": _request},
        "cleanup": lambda: None,
    }


# ── MCP tool adapter ──────────────────────────────────────────────────────────


def _stringify_mcp_content(content: Any) -> str:
    """Convert a list of MCP content blocks into a plain string."""
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        block_type = block.get("type", "")
        if block_type == "text":
            parts.append(block.get("text", ""))
        elif block_type == "image":
            parts.append("[image block]")
        elif block_type == "resource":
            parts.append(block.get("resource", {}).get("text", "[resource block]"))
        else:
            parts.append("[unknown block]")
    return "\n".join(parts)


def build_tool_adapter(
    connection: dict[str, Any], mcp_tool: dict[str, Any]
) -> dict[str, Any]:
    """
    Wrap an MCP tool as a local Tool-compatible dict.

    The adapter translates between the local Tool protocol and the MCP
    ``tools/call`` request format.
    """
    full_name = build_mcp_tool_name(connection["name"], mcp_tool["name"])
    client = connection["client"]

    async def _call(raw_input: dict[str, Any], _context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await client["request"]({
            "method": "tools/call",
            "params": {"name": mcp_tool["name"], "arguments": raw_input},
        })
        return {
            "content": _stringify_mcp_content(result.get("content")),
            "is_error": result.get("isError") is True,
        }

    annotations = mcp_tool.get("annotations") or {}
    return {
        "name": full_name,
        "description": str(mcp_tool.get("description", ""))[:2048],
        "input_schema": mcp_tool.get("inputSchema") or {"type": "object", "properties": {}},
        "is_read_only": lambda: bool(annotations.get("readOnlyHint")),
        "is_enabled": lambda: True,
        "call": _call,
    }


async def fetch_tools_for_connection(connection: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch the tool list from a connected MCP server and wrap each tool."""
    if not connection.get("capabilities", {}).get("tools"):
        return []
    result = await connection["client"]["request"]({"method": "tools/list"})
    return [build_tool_adapter(connection, tool) for tool in result.get("tools", [])]


# ── Bootstrap flow ────────────────────────────────────────────────────────────


async def bootstrap_mcp(
    server_configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Connect to all configured MCP servers and populate the registry.

    Sets each entry to a "pending" stub first, then updates it once
    the connection succeeds (or fails gracefully).
    """
    import asyncio

    clear_mcp_registry()

    # Mark all servers as pending before connecting.
    import time
    for name, config in server_configs.items():
        set_mcp_registry_entry(
            name,
            {"name": name, "type": "pending", "config": config, "started_at": time.time()},
            [],
        )

    # Connect to all servers concurrently.
    async def _connect_one(name: str, config: dict[str, Any]) -> dict[str, Any]:
        connection = await connect_to_server(name, config)
        tools = await fetch_tools_for_connection(connection) if connection["type"] == "connected" else []
        set_mcp_registry_entry(name, connection, tools)
        return {"connection": connection, "tools": tools}

    results = await asyncio.gather(*[
        _connect_one(name, config)
        for name, config in server_configs.items()
    ])

    return {
        "connections": [r["connection"] for r in results],
        "tool_count": sum(len(r["tools"]) for r in results),
    }
