"""
Step 19 - Sub-agents (Task tool)

Goal:
- let the orchestrating agent spawn a focused child agent
- the child inherits a subset of tools and a targeted prompt
- the parent gets a text result, not a shared mutable object
- show how to isolate child context from the parent session

Sub-agents are distinct from parallel agents (step 20): they are
synchronous from the parent's perspective — the parent awaits a result
before continuing.
"""

from __future__ import annotations

import json
import os
from typing import Any, AsyncGenerator

from .step1 import DEFAULT_MODEL, stream_message

# ── Sub-agent system prompt ────────────────────────────────────────────────────

SUBAGENT_SYSTEM_PROMPT = """You are a sub-agent. Your goal is to complete exactly the task described
by the user as accurately and concisely as possible.

Do not engage in conversation. Do not ask clarifying questions.
Begin immediately.

When you have finished, write a comprehensive summary starting with "RESULT:" followed by a
newline, then your findings, conclusions, or artefacts.
"""

# ── Tool contract ─────────────────────────────────────────────────────────────

SubAgentToolList = list[dict[str, Any]]  # Anthropic tools API format


def _create_context_for_subagent(parent_context: dict[str, Any]) -> dict[str, Any]:
    """
    Create a child tool context derived from the parent context.

    The child shares the same working directory and read-only flags but
    has an isolated session ID so its state does not bleed back.
    """
    return {
        "cwd": parent_context.get("cwd", os.getcwd()),
        "session_id": f"subagent-{id(parent_context)}",
        # Child cannot change the permission mode of the parent.
        "permission_mode": "default",
    }


# ── Inner agent loop ──────────────────────────────────────────────────────────


async def run_subagent_loop(
    *,
    prompt: str,
    tools: SubAgentToolList,
    model: str = DEFAULT_MODEL,
    max_turns: int = 20,
    tool_executor: Any | None = None,
) -> dict[str, Any]:
    """
    Drive a child agent loop until it finishes or hits max_turns.

    Args:
        prompt:         The task prompt for the sub-agent.
        tools:          Anthropic-format tool definitions available to the child.
        model:          Model name to use.
        max_turns:      Hard ceiling on the number of turns.
        tool_executor:  Callable ``(content_blocks) -> user_message`` for running
                        tool calls.  When None the child cannot call tools.

    Returns a dict with keys:
        result (str), turn_count (int), usage (dict).
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    total_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

    for turn in range(max_turns):
        gen = stream_message(
            messages=messages,
            model=model,
            system=SUBAGENT_SYSTEM_PROMPT,
            tools=tools or None,
        )

        # Collect the message_done event which carries the assembled message.
        message_done_event: dict[str, Any] | None = None
        async for event in gen:
            if event["type"] == "message_done":
                message_done_event = event

        if message_done_event is None:
            break

        # Accumulate token usage across turns.
        for k in ("input_tokens", "output_tokens"):
            total_usage[k] += message_done_event.get("usage", {}).get(k, 0)

        assistant_msg = message_done_event["assistant_message"]
        stop_reason = message_done_event.get("stop_reason", "end_turn")
        messages.append(assistant_msg)

        # Extract the text result if the model has finished.
        text_blocks = [
            b for b in (assistant_msg.get("content") or [])
            if b.get("type") == "text"
        ]
        combined_text = "\n".join(b.get("text", "") for b in text_blocks)
        if "RESULT:" in combined_text:
            return {
                "result": combined_text,
                "turn_count": turn + 1,
                "usage": total_usage,
            }

        if stop_reason != "tool_use":
            # Model finished without a RESULT: prefix — return its last output.
            return {
                "result": combined_text,
                "turn_count": turn + 1,
                "usage": total_usage,
            }

        # Execute tool calls and feed results back if a tool_executor is provided.
        if tool_executor is None:
            break

        tool_result_msg = await tool_executor(assistant_msg.get("content", []))
        messages.append(tool_result_msg)

    return {
        "result": "Sub-agent did not produce a result within the turn limit.",
        "turn_count": max_turns,
        "usage": total_usage,
    }


# ── Task tool ─────────────────────────────────────────────────────────────────


class TaskTool:
    """
    Spawn a sub-agent to handle a focused task.

    The Task tool gives the orchestrating model a way to delegate complex
    sub-problems without polluting the parent conversation history.
    The parent receives a single ``result`` string when the sub-agent finishes.
    """

    name = "Task"
    description = (
        "Spawn a sub-agent to complete a specific task. "
        "The sub-agent works independently and returns a text result. "
        "Use for complex or self-contained tasks that don't need interactive feedback."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Detailed task description (what to do and what to return).",
            },
            "prompt": {
                "type": "string",
                "description": "The exact user message for the sub-agent.",
            },
        },
        "required": ["description", "prompt"],
    }

    def is_read_only(self) -> bool:
        return False  # sub-agents can write files

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = input.get("prompt") or input.get("description", "")
        if not prompt:
            return {"content": "Error: prompt is required", "is_error": True}

        # Build a minimal read-only tool set for the sub-agent.
        from .step5 import read_tool, grep_tool, glob_tool, bash_tool

        available_tools: list[dict[str, Any]] = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in [read_tool, grep_tool, glob_tool, bash_tool]
        ]

        child_context = _create_context_for_subagent(context)

        async def _execute_tools(
            content_blocks: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Execute tool calls on behalf of the sub-agent."""
            results = []
            for block in content_blocks:
                if block.get("type") != "tool_use":
                    continue
                tool_map = {
                    t.name: t for t in [read_tool, grep_tool, glob_tool, bash_tool]
                }
                tool = tool_map.get(block["name"])
                if tool is None:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": f"Error: unknown tool {block['name']}",
                        "is_error": True,
                    })
                    continue
                result = await tool.call(block.get("input", {}), child_context)
                entry: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": result["content"],
                }
                if result.get("is_error"):
                    entry["is_error"] = True
                results.append(entry)
            return {"role": "user", "content": results}

        sub_result = await run_subagent_loop(
            prompt=prompt,
            tools=available_tools,
            tool_executor=_execute_tools,
        )

        usage_str = json.dumps(sub_result["usage"])
        return {
            "content": "\n\n".join([
                f"Task completed in {sub_result['turn_count']} turn(s).",
                f"Usage: {usage_str}",
                sub_result["result"],
            ])
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

task_tool = TaskTool()
