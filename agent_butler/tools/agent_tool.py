from __future__ import annotations

import random
import time
from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


def _generate_agent_id() -> str:
    return f"{int(time.time() * 1000):x}-{random.getrandbits(32):08x}"


class AgentTool(Tool):
    @property
    def name(self) -> str:
        return "Agent"

    @property
    def description(self) -> str:
        return (
            "Delegate a focused subtask to a specialized sub-agent. "
            "The sub-agent runs in its own context window with its own tool set."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Self-contained task description for the sub-agent."},
                "description": {"type": "string", "description": "A short (3-5 word) name for the task."},
                "subagent_type": {"type": "string", "description": "Which sub-agent definition to use."},
                "model": {"type": "string", "description": "Optional model override."},
                "run_in_background": {"type": "boolean", "description": "If true, run in background."},
                "isolation": {"type": "string", "enum": ["none", "worktree"]},
            },
            "required": ["prompt", "description"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        prompt = input_data.get("prompt", "")
        description = input_data.get("description", "")
        subagent_type = input_data.get("subagent_type", "general-purpose") or "general-purpose"
        model_override = input_data.get("model")
        run_in_background = input_data.get("run_in_background", False)

        if not prompt or not str(prompt).strip():
            return ToolResult(content="Error: 'prompt' is required.", is_error=True)

        from ..agents.registry import find_agent, get_all_agents
        from ..services.api.client import DEFAULT_MODEL

        defn = find_agent(subagent_type)
        if not defn:
            available = ", ".join(a["agent_type"] for a in get_all_agents())
            return ToolResult(
                content=f"Error: sub-agent type '{subagent_type}' not registered. Available: {available or '(none)'}.",
                is_error=True,
            )

        from ..tools.registry import get_all_tools
        all_tools = get_all_tools()

        resolved_model = (
            model_override
            or defn.get("model")
            or (context.default_model if context.default_model else None)
            or DEFAULT_MODEL
        )

        if run_in_background:
            agent_id = _generate_agent_id()
            session_id = context.session_id or "default"

            from ..utils.task_output import ensure_task_output_file
            output_file = await ensure_task_output_file(session_id, agent_id)

            from ..state.async_agent_store import register_async_agent
            register_async_agent({
                "agent_id": agent_id,
                "agent_type": subagent_type,
                "description": description,
                "prompt": prompt,
                "output_file": output_file,
            })

            from ..agents.run_async_agent import run_async_agent_lifecycle
            import asyncio
            asyncio.create_task(run_async_agent_lifecycle({
                "agent_id": agent_id,
                "agent_definition": defn,
                "prompt": prompt,
                "description": description,
                "available_tools": all_tools,
                "model": resolved_model,
                "parent_tool_context": context,
            }))

            return ToolResult(content="\n".join([
                f"Async sub-agent '{subagent_type}' launched successfully.",
                f"agent_id: {agent_id}",
                f"output_file: {output_file}",
                "",
                "The agent is working in the background.",
            ]))

        progress_key = context.tool_use_id

        try:
            from ..agents.run_agent import run_child_agent
            result = await run_child_agent({
                "agent_definition": defn,
                "prompt": prompt,
                "available_tools": all_tools,
                "model": resolved_model,
                "parent_tool_context": context,
            })

            header = "\n".join(filter(None, [
                f"Sub-agent '{subagent_type}' completed.",
                f"task: {description}" if description else None,
                f"turns: {result.get('turn_count', 0)} | tools: {result.get('total_tool_use_count', 0)} | duration: {result.get('total_duration_ms', 0)}ms",
            ]))
            return ToolResult(content=f"{header}\n\n<sub_agent_result>\n{result.get('final_text', '')}\n</sub_agent_result>")
        except Exception as e:
            return ToolResult(content=f"Error: sub-agent '{subagent_type}' failed: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return True


agent_tool = AgentTool()
