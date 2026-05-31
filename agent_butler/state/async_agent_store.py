from __future__ import annotations

from typing import Any

_async_agents: dict[str, dict[str, Any]] = {}


def register_async_agent(entry: dict[str, Any]) -> dict[str, Any]:
    agent_id = entry.get("agent_id", "")
    record = {
        "agent_id": agent_id,
        "agent_type": entry.get("agent_type", ""),
        "description": entry.get("description", ""),
        "prompt": entry.get("prompt", ""),
        "output_file": entry.get("output_file"),
        "status": "running",
        "result": None,
    }
    _async_agents[agent_id] = record
    return record


def get_async_agent(agent_id: str) -> dict[str, Any] | None:
    return _async_agents.get(agent_id)


def complete_async_agent(agent_id: str, result: dict[str, Any]) -> None:
    agent = _async_agents.get(agent_id)
    if agent:
        agent["status"] = "completed"
        agent["result"] = result


def get_all_async_agents() -> list[dict[str, Any]]:
    return list(_async_agents.values())


def remove_async_agent(agent_id: str) -> bool:
    return _async_agents.pop(agent_id, None) is not None
