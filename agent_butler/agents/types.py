from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AgentIsolation = Literal["none", "worktree"]


@dataclass
class AgentDefinition:
    agent_type: str
    description: str
    system_prompt: str
    model: str | None = None
    tools_allow: list[str] = field(default_factory=list)
    tools_deny: list[str] = field(default_factory=list)
    isolation: AgentIsolation = "none"
    max_turns: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    final_text: str = ""
    reason: str = ""
    turn_count: int = 0
    total_tool_use_count: int = 0
    total_duration_ms: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
