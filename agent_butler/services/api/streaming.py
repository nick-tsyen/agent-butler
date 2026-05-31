from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from ...types.message import (
    AssistantMessage,
    ContentBlock,
    StreamErrorEvent,
    StreamEvent,
    StreamMessageDoneEvent,
    StreamMessageStartEvent,
    StreamTextEvent,
    StreamToolUseInputEvent,
    StreamToolUseStartEvent,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    Usage,
)
from ...utils.stream_debug import write_stream_debug
from .client import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    ESCALATED_MAX_TOKENS,
    get_anthropic_client,
)


@dataclass
class StreamRequestParams:
    messages: list[dict[str, Any]]
    model: str | None = None
    max_tokens: int | None = None
    system: str | None = None
    tools: list[dict[str, Any]] | None = None
    abort_event: Any | None = None


@dataclass
class StreamResult:
    assistant_message: AssistantMessage
    usage: Usage
    stop_reason: str


_SENTINEL_RESULT = StreamResult(
    assistant_message=AssistantMessage(content=[]),
    usage=Usage(input_tokens=0, output_tokens=0),
    stop_reason="error",
)


async def stream_message(params: StreamRequestParams) -> AsyncGenerator[StreamEvent, StreamResult]:
    client = get_anthropic_client()
    model = params.model or DEFAULT_MODEL
    max_tokens = params.max_tokens or DEFAULT_MAX_TOKENS

    request_params: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": params.messages,
    }
    if params.system:
        request_params["system"] = params.system
    if params.tools and len(params.tools) > 0:
        request_params["tools"] = params.tools

    content_blocks: list[ContentBlock | None] = []
    tool_input_json_by_index: dict[int, str] = {}
    message_id = ""
    stop_reason = ""
    usage = Usage(input_tokens=0, output_tokens=0)

    write_stream_debug("request", {
        "model": model,
        "messageCount": len(params.messages),
        "toolNames": [t.get("name") for t in params.tools] if params.tools else None,
    })

    try:
        with client.messages.stream(**request_params) as stream:
            for event in stream:
                write_stream_debug("event", str(event))

                event_type = event.type

                if event_type == "message_start":
                    msg = event.message
                    message_id = msg.id
                    if msg.usage:
                        usage.input_tokens = msg.usage.input_tokens
                        usage.output_tokens = msg.usage.output_tokens
                        if hasattr(msg.usage, "cache_creation_input_tokens") and msg.usage.cache_creation_input_tokens:
                            usage.cache_creation_input_tokens = msg.usage.cache_creation_input_tokens
                        if hasattr(msg.usage, "cache_read_input_tokens") and msg.usage.cache_read_input_tokens:
                            usage.cache_read_input_tokens = msg.usage.cache_read_input_tokens
                    yield StreamMessageStartEvent(message_id=message_id)

                elif event_type == "message_delta":
                    if hasattr(event, "usage") and event.usage:
                        usage.output_tokens = event.usage.output_tokens
                    if hasattr(event, "delta") and hasattr(event.delta, "stop_reason"):
                        stop_reason = event.delta.stop_reason or ""

                elif event_type == "message_stop":
                    yield StreamMessageDoneEvent(stop_reason=stop_reason, usage=usage)

                elif event_type == "content_block_start":
                    index = event.index
                    cb = event.content_block

                    if cb.type == "text":
                        while len(content_blocks) <= index:
                            content_blocks.append(None)
                        content_blocks[index] = TextBlock(text="")
                    elif cb.type == "thinking":
                        while len(content_blocks) <= index:
                            content_blocks.append(None)
                        content_blocks[index] = ThinkingBlock(thinking=getattr(cb, "thinking", "") or "")
                    elif cb.type == "tool_use":
                        seed_input = {}
                        if hasattr(cb, "input") and isinstance(cb.input, dict):
                            seed_input = cb.input
                        while len(content_blocks) <= index:
                            content_blocks.append(None)
                        content_blocks[index] = ToolUseBlock(id=cb.id, name=cb.name, input=seed_input)
                        tool_input_json_by_index[index] = ""
                        yield StreamToolUseStartEvent(id=cb.id, name=cb.name)

                elif event_type == "content_block_delta":
                    delta = event.delta
                    index = event.index

                    if delta.type == "text_delta":
                        block = content_blocks[index] if index < len(content_blocks) else None
                        if block and isinstance(block, TextBlock):
                            block.text += delta.text
                        yield StreamTextEvent(text=delta.text)
                    elif delta.type == "thinking_delta":
                        block = content_blocks[index] if index < len(content_blocks) else None
                        if block and isinstance(block, ThinkingBlock):
                            block.thinking += getattr(delta, "thinking", "") or ""
                    elif delta.type == "signature_delta":
                        block = content_blocks[index] if index < len(content_blocks) else None
                        if block and isinstance(block, ThinkingBlock):
                            sig = getattr(delta, "signature", "") or ""
                            block.signature = (block.signature or "") + sig
                    elif delta.type == "input_json_delta":
                        prev = tool_input_json_by_index.get(index, "")
                        tool_input_json_by_index[index] = prev + delta.partial_json
                        block = content_blocks[index] if index < len(content_blocks) else None
                        if block and isinstance(block, ToolUseBlock):
                            yield StreamToolUseInputEvent(id=block.id, partial_json=delta.partial_json)

                elif event_type == "content_block_stop":
                    index = event.index
                    block = content_blocks[index] if index < len(content_blocks) else None
                    accumulated = tool_input_json_by_index.get(index)
                    if block and isinstance(block, ToolUseBlock) and accumulated:
                        try:
                            block.input = json.loads(accumulated)
                        except json.JSONDecodeError:
                            block.input = {"_raw": accumulated}
                    tool_input_json_by_index.pop(index, None)

    except Exception as e:
        write_stream_debug("stream_error", {"message": str(e)})
        yield StreamErrorEvent(error=str(e))

    write_stream_debug("assembled", {
        "stop_reason": stop_reason,
        "block_count": sum(1 for b in content_blocks if b is not None),
    })

    yield _SENTINEL_RESULT


async def create_message(
    params: StreamRequestParams,
) -> dict[str, Any]:
    client = get_anthropic_client()
    model = params.model or DEFAULT_MODEL
    max_tokens = params.max_tokens or DEFAULT_MAX_TOKENS

    request_params: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": params.messages,
    }
    if params.system:
        request_params["system"] = params.system
    if params.tools and len(params.tools) > 0:
        request_params["tools"] = params.tools

    response = client.messages.create(**request_params)

    content_blocks: list[ContentBlock] = []
    for block in response.content:
        if block.type == "text":
            content_blocks.append(TextBlock(text=block.text))
        elif block.type == "tool_use":
            content_blocks.append(ToolUseBlock(id=block.id, name=block.name, input=block.input))

    usage_result = Usage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    if hasattr(response.usage, "cache_creation_input_tokens") and response.usage.cache_creation_input_tokens:
        usage_result.cache_creation_input_tokens = response.usage.cache_creation_input_tokens
    if hasattr(response.usage, "cache_read_input_tokens") and response.usage.cache_read_input_tokens:
        usage_result.cache_read_input_tokens = response.usage.cache_read_input_tokens

    return {
        "content": content_blocks,
        "usage": usage_result,
        "stop_reason": response.stop_reason or "end_turn",
    }


async def stream_message_with_retry(params: StreamRequestParams) -> AsyncGenerator[StreamEvent, StreamResult]:
    events: list[StreamEvent] = []
    result: StreamResult | None = None

    gen = stream_message(params)
    try:
        while True:
            event = await gen.__anext__()
            if isinstance(event, StreamResult):
                result = event
                break
            events.append(event)
            yield event
    except StopAsyncIteration:
        pass

    if result is None:
        result = StreamResult(
            assistant_message=AssistantMessage(content=[]),
            usage=Usage(input_tokens=0, output_tokens=0),
            stop_reason="error",
        )

    if result.stop_reason != "max_tokens":
        return

    escalated_gen = stream_message(StreamRequestParams(
        messages=params.messages,
        model=params.model,
        max_tokens=ESCALATED_MAX_TOKENS,
        system=params.system,
        tools=params.tools,
        abort_event=params.abort_event,
    ))
    escalated_events: list[StreamEvent] = []
    escalated_result: StreamResult | None = None
    try:
        while True:
            event = await escalated_gen.__anext__()
            if isinstance(event, StreamResult):
                escalated_result = event
                break
            escalated_events.append(event)
    except StopAsyncIteration:
        pass

    if escalated_result is None:
        return

    if escalated_result.stop_reason != "max_tokens":
        for ev in escalated_events:
            yield ev
        return

    for ev in escalated_events:
        yield ev
