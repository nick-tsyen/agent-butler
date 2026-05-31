from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .types import AgentDefinition

logger = logging.getLogger(__name__)


def _parse_agent_json(data: dict[str, Any]) -> AgentDefinition | None:
    agent_type = data.get("agent_type") or data.get("type")
    if not agent_type or not isinstance(agent_type, str):
        return None

    isolation = data.get("isolation", "none")
    if isolation not in ("none", "worktree"):
        isolation = "none"

    return AgentDefinition(
        agent_type=agent_type,
        description=data.get("description", ""),
        system_prompt=data.get("system_prompt", ""),
        model=data.get("model"),
        tools_allow=data.get("tools_allow", []),
        tools_deny=data.get("tools_deny", []),
        isolation=isolation,  # type: ignore[arg-type]
        max_turns=data.get("max_turns", 100),
        metadata=data.get("metadata", {}),
    )


async def load_agents_from_dir(dir_path: str) -> list[AgentDefinition]:
    agents_dir = Path(dir_path)
    if not agents_dir.is_dir():
        return []

    definitions: list[AgentDefinition] = []

    for json_file in sorted(agents_dir.glob("*.json")):
        try:
            text = json_file.read_text(encoding="utf-8")
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        defn = _parse_agent_json(item)
                        if defn:
                            definitions.append(defn)
            elif isinstance(data, dict):
                defn = _parse_agent_json(data)
                if defn:
                    definitions.append(defn)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load agent from {json_file}: {e}")

    return definitions
