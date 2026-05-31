from __future__ import annotations

from .normalization import normalize_name_for_mcp


def mcp_tool_name(server_name: str, tool_name: str) -> str:
    return f"mcp__{normalize_name_for_mcp(server_name)}__{normalize_name_for_mcp(tool_name)}"


def is_mcp_tool_name(name: str) -> bool:
    return name.startswith("mcp__")


def parse_mcp_tool_name(full_name: str) -> dict[str, str] | None:
    parts = full_name.split("__")
    if len(parts) < 3 or parts[0] != "mcp" or not parts[1]:
        return None
    return {
        "serverName": parts[1],
        "toolName": "__".join(parts[2:]),
    }
