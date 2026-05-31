from __future__ import annotations

from ..types import AgentDefinition

AGENT_DEFINITION = AgentDefinition(
    agent_type="general-purpose",
    description="General-purpose sub-agent with full tool access for autonomous task completion.",
    system_prompt=(
        "You are a general-purpose coding sub-agent. You have been delegated a focused "
        "subtask by a parent agent. Complete the task autonomously using the tools available "
        "to you. Be thorough but concise. When finished, provide a clear summary of what "
        "you did and any relevant findings."
    ),
    model=None,
    tools_allow=[],
    tools_deny=[],
    isolation="none",
    max_turns=100,
)
