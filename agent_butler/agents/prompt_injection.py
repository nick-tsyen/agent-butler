from __future__ import annotations

from .types import AgentDefinition


def inject_agent_prompt(prompt: str, agent_def: AgentDefinition) -> str:
    parts: list[str] = []

    if agent_def.system_prompt:
        parts.append(agent_def.system_prompt)

    parts.append(prompt)

    if agent_def.tools_deny:
        deny_list = ", ".join(agent_def.tools_deny)
        parts.append(f"\nNote: The following tools are unavailable: {deny_list}")

    return "\n\n".join(parts)
