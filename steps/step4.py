"""
Step 4 - Minimal Agentic Loop

Goal:
- let the model request tools
- execute tools
- feed tool results back into the conversation
- continue until the model finishes the turn
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from .step1 import stream_message
from .step3 import find_tool_by_name, get_tools_api_params

# ── Tool execution ─────────────────────────────────────────────────────────────


async def run_tools(
    content_blocks: list[dict[str, Any]],
    tool_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute all tool_use blocks in *content_blocks* and return a user message
    containing the tool results.

    Unknown tools produce an error result rather than raising an exception so
    the loop can continue and the model can react to the error.
    """
    results: list[dict[str, Any]] = []

    for block in content_blocks:
        if block.get("type") != "tool_use":
            continue  # skip text blocks

        tool = find_tool_by_name(block["name"])
        if tool is None:
            # Report unknown tool as an error result.
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": f"Error: unknown tool {block['name']}",
                    "is_error": True,
                }
            )
            continue

        result = await tool.call(block.get("input", {}), tool_context)
        entry: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": block["id"],
            "content": result["content"],
        }
        if result.get("is_error"):
            entry["is_error"] = True
        results.append(entry)

    # Wrap results in a user message so they re-enter the conversation.
    return {"role": "user", "content": results}


# ── Agentic loop ───────────────────────────────────────────────────────────────


async def query(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    system_prompt: str | None = None,
    tool_context: dict[str, Any] | None = None,
    max_turns: int = 8,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Run the agentic loop: stream → tool execution → stream → … until done.

    Yields low-level stream events so the caller (UI layer) can render
    output in real time.  Also yields higher-level events:
      - {"type": "assistant_message", "message": dict}
      - {"type": "tool_result_message", "message": dict}
      - {"type": "query_done", "state": dict, "usage": dict, "reason": str}

    The final "query_done" event carries the overall result.
    """
    return _query_impl(
        messages=messages,
        model=model,
        system_prompt=system_prompt,
        tool_context=tool_context or {},
        max_turns=max_turns,
    )


async def _query_impl(
    *,
    messages: list[dict[str, Any]],
    model: str | None,
    system_prompt: str | None,
    tool_context: dict[str, Any],
    max_turns: int,
) -> AsyncGenerator[dict[str, Any], None]:
    """Internal async generator that drives the agentic loop."""

    state: dict[str, Any] = {
        "messages": list(messages),  # mutable copy
        "turn_count": 0,
    }

    while state["turn_count"] < max_turns:
        state["turn_count"] += 1

        # Build stream kwargs — only include optional params when set.
        stream_kwargs: dict[str, Any] = {
            "messages": state["messages"],
            "tools": get_tools_api_params(),
        }
        if model:
            stream_kwargs["model"] = model
        if system_prompt:
            stream_kwargs["system"] = system_prompt

        gen = stream_message(**stream_kwargs)

        # The "message_done" event carries the assembled assistant message.
        message_done_event: dict[str, Any] | None = None

        async for event in gen:
            if event["type"] == "message_done":
                message_done_event = event
            else:
                # Re-yield low-level stream events to the UI layer.
                yield event

        if message_done_event is None:
            break  # stream ended unexpectedly

        assistant_msg = message_done_event["assistant_message"]
        stop_reason = message_done_event.get("stop_reason", "end_turn")
        turn_usage = message_done_event.get("usage", {})

        state["messages"].append(assistant_msg)
        yield {"type": "assistant_message", "message": assistant_msg}

        if stop_reason != "tool_use":
            # Model finished without requesting any tools — we're done.
            yield {
                "type": "query_done",
                "state": state,
                "usage": turn_usage,
                "reason": "completed",
            }
            return

        # Execute all requested tool calls and feed results back.
        tool_result_message = await run_tools(assistant_msg["content"], tool_context)
        state["messages"].append(tool_result_message)
        yield {"type": "tool_result_message", "message": tool_result_message}

    # Reached the turn limit without finishing.
    yield {
        "type": "query_done",
        "state": state,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "reason": "max_turns",
    }
