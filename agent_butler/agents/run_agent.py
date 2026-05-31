from __future__ import annotations

from typing import Any

from ..core.agentic_loop import query
from .types import AgentRunResult


async def run_child_agent(params: dict[str, Any]) -> dict[str, Any]:
    agent_definition: dict[str, Any] = params["agent_definition"]
    prompt: str = params["prompt"]
    available_tools = params.get("available_tools", [])
    model: str | None = params.get("model")
    parent_context = params.get("parent_tool_context")

    system_prompt = agent_definition.get("system_prompt", "")
    max_turns = agent_definition.get("max_turns", 100)

    tools_allow = set(agent_definition.get("tools_allow", []))
    tools_deny = set(agent_definition.get("tools_deny", []))

    if tools_allow:
        resolved_tools = [t for t in available_tools if t.name in tools_allow]
    elif tools_deny:
        resolved_tools = [t for t in available_tools if t.name not in tools_deny]
    else:
        resolved_tools = list(available_tools)

    cwd = parent_context.cwd if parent_context else "."

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": prompt},
    ]

    final_text_parts: list[str] = []
    turn_count = 0
    total_tool_use_count = 0
    total_duration_ms = 0
    last_usage: dict[str, Any] = {}
    stop_reason = ""

    async for event in query(
        messages=messages,
        system_prompt=system_prompt,
        tools=resolved_tools,
        model=model,
        cwd=cwd,
        max_turns=max_turns,
        session_id=parent_context.session_id if parent_context else None,
    ):
        event_type = event.get("type")

        if event_type == "text":
            final_text_parts.append(event.get("text", ""))

        elif event_type == "result":
            turn_count = event.get("turn_count", 0)
            total_tool_use_count = event.get("total_tool_use_count", 0)
            total_duration_ms = event.get("total_duration_ms", 0)
            stop_reason = event.get("stop_reason", "")
            last_usage = event.get("usage", {})
            assistant_msg = event.get("assistant_message", {})
            content = assistant_msg.get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    final_text_parts.append(block.get("text", ""))

        elif event_type == "max_turns_reached":
            turn_count = event.get("turn_count", 0)
            total_tool_use_count = event.get("total_tool_use_count", 0)
            total_duration_ms = event.get("total_duration_ms", 0)

    result = AgentRunResult(
        final_text="".join(final_text_parts),
        reason=stop_reason or "completed",
        turn_count=turn_count,
        total_tool_use_count=total_tool_use_count,
        total_duration_ms=total_duration_ms,
        usage=last_usage,
    )

    return {
        "final_text": result.final_text,
        "reason": result.reason,
        "turn_count": result.turn_count,
        "total_tool_use_count": result.total_tool_use_count,
        "total_duration_ms": result.total_duration_ms,
        "usage": result.usage,
    }
