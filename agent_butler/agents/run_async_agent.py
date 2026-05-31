from __future__ import annotations

import logging
from typing import Any

from ..state.async_agent_store import complete_async_agent
from ..utils.task_output import append_task_output
from .run_agent import run_child_agent

logger = logging.getLogger(__name__)


async def run_async_agent_lifecycle(params: dict[str, Any]) -> None:
    agent_id: str = params["agent_id"]
    output_file: str | None = params.get("output_file")

    try:
        if output_file:
            await append_task_output(output_file, {
                "type": "agent_start",
                "agent_id": agent_id,
                "description": params.get("description", ""),
            })

        result = await run_child_agent(params)

        complete_async_agent(agent_id, result)

        if output_file:
            await append_task_output(output_file, {
                "type": "agent_complete",
                "agent_id": agent_id,
                "result": result,
            })

    except Exception as e:
        logger.error(f"Async agent {agent_id} failed: {e}")
        complete_async_agent(agent_id, {"error": str(e), "final_text": ""})

        if output_file:
            await append_task_output(output_file, {
                "type": "agent_error",
                "agent_id": agent_id,
                "error": str(e),
            })
