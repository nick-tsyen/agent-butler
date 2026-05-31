from __future__ import annotations

from ..tools.base import Tool
from .types import AgentDefinition


def resolve_agent_tools(
    agent_def: AgentDefinition,
    all_tools: list[Tool],
) -> list[Tool]:
    if agent_def.tools_allow:
        allowed = set(agent_def.tools_allow)
        return [t for t in all_tools if t.name in allowed and t.is_enabled()]

    if agent_def.tools_deny:
        denied = set(agent_def.tools_deny)
        return [t for t in all_tools if t.name not in denied and t.is_enabled()]

    return [t for t in all_tools if t.is_enabled()]
