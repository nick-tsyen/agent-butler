from __future__ import annotations

from .types import AgentDefinition

_agent_registry: dict[str, AgentDefinition] = {}


def register_agent(defn: AgentDefinition) -> None:
    _agent_registry[defn.agent_type] = defn


def find_agent(agent_type: str) -> AgentDefinition | None:
    return _agent_registry.get(agent_type)


def get_all_agents() -> list[AgentDefinition]:
    return list(_agent_registry.values())


def unregister_agent(agent_type: str) -> bool:
    return _agent_registry.pop(agent_type, None) is not None


def clear_registry() -> None:
    _agent_registry.clear()
