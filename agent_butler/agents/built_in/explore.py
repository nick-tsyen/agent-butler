from __future__ import annotations

from ..types import AgentDefinition

AGENT_DEFINITION = AgentDefinition(
    agent_type="explore",
    description="Read-only exploration agent for searching and understanding codebases.",
    system_prompt=(
        "You are a read-only code exploration agent. Your job is to search, read, and "
        "understand code in the current project. You may use Read, Grep, and Glob tools "
        "to find and examine files. Do NOT modify any files or run any commands that "
        "change state. Provide a clear, concise summary of your findings."
    ),
    model=None,
    tools_allow=["Read", "Grep", "Glob"],
    tools_deny=[],
    isolation="none",
    max_turns=30,
)
