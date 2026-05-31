from __future__ import annotations

from typing import Any

from .base import Tool, tool_to_api_param

_builtin_tools: list[Tool] = []
_mcp_tools: list[Tool] = []


def register_mcp_tools(tools: list[Tool]) -> None:
    global _mcp_tools
    _mcp_tools = list(tools)


def clear_mcp_tools() -> None:
    global _mcp_tools
    _mcp_tools = []


def _all_raw() -> list[Tool]:
    return [*_builtin_tools, *_mcp_tools]


def get_all_tools() -> list[Tool]:
    return [t for t in _all_raw() if t.is_enabled()]


def find_tool_by_name(name: str) -> Tool | None:
    for t in _all_raw():
        if t.name == name:
            return t
    return None


def get_tools_api_params(mode: str | None = None) -> list[dict[str, Any]]:
    tools = get_all_tools()
    if mode == "plan":
        return [tool_to_api_param(t) for t in tools if t.name != "EnterPlanMode"]
    return [tool_to_api_param(t) for t in tools if t.name != "ExitPlanMode"]


def register_builtin_tools(tools: list[Tool]) -> None:
    global _builtin_tools
    _builtin_tools = list(tools)
