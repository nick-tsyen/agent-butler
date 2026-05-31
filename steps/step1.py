"""
Step 1 - Minimal LLM streaming client

Goal:
- show the smallest useful Anthropic client wrapper
- stream text and tool-use events
- keep the code in one file for teaching purposes

This file is intentionally simpler than agent-butler/src/services/api/*.
"""

import json
import os
from typing import Any, AsyncGenerator

import anthropic

# Default model and token budget — override via env vars.
DEFAULT_MODEL: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEFAULT_MAX_TOKENS: int = 4096


def get_client() -> anthropic.AsyncAnthropic:
    """Create one shared async SDK client using env-var credentials."""
    return anthropic.AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN"),
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )


# ── Content block helpers ──────────────────────────────────────────────────────
# Content blocks are the core message shape in Anthropic's Messages API.


def text_block(text: str = "") -> dict[str, Any]:
    """Return a text content block."""
    return {"type": "text", "text": text}


def tool_use_block(id: str, name: str, input: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a tool_use content block."""
    return {"type": "tool_use", "id": id, "name": name, "input": input or {}}


# ── Stream event types ────────────────────────────────────────────────────────

# Each yielded event is a plain dict with at least a "type" key.
# The final "message_done" event also carries the full assembled message:
#
#   {"type": "message_done",
#    "stop_reason": str,
#    "usage": {"input_tokens": int, "output_tokens": int},
#    "assistant_message": {"role": "assistant", "content": list}}
#
StreamEvent = dict[str, Any]


async def stream_message(
    *,
    messages: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Stream one assistant turn.

    Yields small events so the caller can render text in real time.
    The *final* event has type ``"message_done"`` and includes the full
    assembled assistant message plus usage.

    Yields:
        - {"type": "message_start", "message_id": str}
        - {"type": "tool_use_start", "id": str, "name": str}
        - {"type": "text", "text": str}
        - {"type": "message_done", "stop_reason": str,
           "usage": dict, "assistant_message": dict}
    """
    client = get_client()

    # Build the request kwargs dynamically — only include optional params when set.
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    # content is a sparse list indexed by content_block index from the stream.
    content: list[dict[str, Any]] = []
    usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    stop_reason: str = "end_turn"
    pending_tool_json: str = ""  # accumulates partial JSON for tool inputs

    async with client.messages.stream(**kwargs) as stream:
        async for event in stream:
            # Dispatch on the raw event type string.
            event_type = event.type

            if event_type == "message_start":
                # Capture initial token count reported by the API.
                usage["input_tokens"] = getattr(event.message.usage, "input_tokens", 0) or 0
                yield {"type": "message_start", "message_id": event.message.id}

            elif event_type == "content_block_start":
                cb = event.content_block
                idx = event.index

                if cb.type == "text":
                    # Ensure list is large enough, then initialise slot.
                    while len(content) <= idx:
                        content.append({})
                    content[idx] = text_block("")

                elif cb.type == "tool_use":
                    while len(content) <= idx:
                        content.append({})
                    content[idx] = tool_use_block(cb.id, cb.name)
                    pending_tool_json = ""  # reset accumulator for this tool call
                    yield {"type": "tool_use_start", "id": cb.id, "name": cb.name}

            elif event_type == "content_block_delta":
                delta = event.delta
                idx = event.index

                if delta.type == "text_delta":
                    # Append incremental text to the current block.
                    content[idx]["text"] += delta.text
                    yield {"type": "text", "text": delta.text}

                elif delta.type == "input_json_delta":
                    # Accumulate JSON fragments; parse only when the block stops.
                    pending_tool_json += delta.partial_json

            elif event_type == "content_block_stop":
                block = content[event.index] if event.index < len(content) else None
                if block and block.get("type") == "tool_use" and pending_tool_json:
                    # Parse the fully accumulated JSON input for the tool call.
                    block["input"] = json.loads(pending_tool_json)
                    pending_tool_json = ""

            elif event_type == "message_delta":
                # Update output token count and stop reason as they arrive.
                usage["output_tokens"] = getattr(event.usage, "output_tokens", usage["output_tokens"]) or usage["output_tokens"]
                stop_reason = getattr(event.delta, "stop_reason", None) or stop_reason

            elif event_type == "message_stop":
                # Final event: include the fully assembled message and usage.
                # Python async generators cannot return a value, so we embed
                # the result in this last yielded event instead.
                yield {
                    "type": "message_done",
                    "stop_reason": stop_reason,
                    "usage": dict(usage),
                    "assistant_message": {"role": "assistant", "content": content},
                }
