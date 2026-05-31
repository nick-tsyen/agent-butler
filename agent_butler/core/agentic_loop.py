from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Callable

from ..permissions.permissions import (
    PermissionRuleSet,
    PermissionSettings,
    check_permission,
)
from ..services.api.streaming import StreamRequestParams, stream_message_with_retry
from ..tools.base import Tool, tool_to_api_param
from ..types.message import ContentBlock, ToolUseBlock
from ..types.tool import ToolContext


def partition_tool_calls(
    tool_calls: list[dict[str, Any]],
    tools: list[Tool],
) -> list[list[dict[str, Any]]]:
    tool_map = {t.name: t for t in tools}
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_is_concurrent = True

    for tc in tool_calls:
        name = tc.get("name", "")
        tool = tool_map.get(name)
        is_safe = tool.is_concurrency_safe(tc.get("input")) if tool else False

        if is_safe and current_is_concurrent:
            current_batch.append(tc)
        elif not is_safe and not current_is_concurrent:
            current_batch.append(tc)
        else:
            if current_batch:
                batches.append(current_batch)
            current_batch = [tc]
            current_is_concurrent = is_safe

    if current_batch:
        batches.append(current_batch)

    return batches


async def run_tools(
    tool_calls: list[dict[str, Any]],
    tools: list[Tool],
    context: ToolContext,
    permission_settings: PermissionSettings | None = None,
    session_rules: PermissionRuleSet | None = None,
    on_permission_request: Callable | None = None,
) -> list[dict[str, Any]]:
    tool_map = {t.name: t for t in tools}
    results: list[dict[str, Any]] = []

    batches = partition_tool_calls(tool_calls, tools)

    for batch in batches:
        if len(batch) == 1:
            result = await _execute_single_tool(
                batch[0],
                tool_map,
                context,
                permission_settings,
                session_rules,
                on_permission_request,
            )
            results.append(result)
        else:
            coros = [
                _execute_single_tool(
                    tc,
                    tool_map,
                    context,
                    permission_settings,
                    session_rules,
                    on_permission_request,
                )
                for tc in batch
            ]
            batch_results = await asyncio.gather(*coros, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, Exception):
                    results.append({
                        "tool_use_id": "",
                        "content": f"Error: {r}",
                        "is_error": True,
                    })
                else:
                    results.append(r)

    return results


async def _execute_single_tool(
    tool_call: dict[str, Any],
    tool_map: dict[str, Tool],
    context: ToolContext,
    permission_settings: PermissionSettings | None,
    session_rules: PermissionRuleSet | None,
    on_permission_request: Callable | None,
) -> dict[str, Any]:
    name = tool_call.get("name", "")
    tool_input = tool_call.get("input", {})
    tool_use_id = tool_call.get("id", "")

    tool = tool_map.get(name)
    if not tool:
        return {
            "tool_use_id": tool_use_id,
            "content": f"Error: Unknown tool '{name}'",
            "is_error": True,
        }

    perm_response = await check_permission(
        tool,
        tool_input,
        context.cwd,
        settings=permission_settings,
        session_rules=session_rules,
        on_permission_request=on_permission_request,
    )

    if perm_response.behavior == "deny":
        return {
            "tool_use_id": tool_use_id,
            "content": f"Permission denied: {perm_response.reason}",
            "is_error": True,
        }

    if perm_response.behavior == "ask" and on_permission_request:
        decision = await on_permission_request(perm_response.request)
        if not decision or decision.get("behavior") == "deny":
            return {
                "tool_use_id": tool_use_id,
                "content": "Permission denied by user.",
                "is_error": True,
            }

    try:
        tool_context = context.model_copy(update={"tool_use_id": tool_use_id})
        result = await tool.call(tool_input, tool_context)
        return {
            "tool_use_id": tool_use_id,
            "content": result.content,
            "is_error": result.is_error or False,
        }
    except Exception as e:
        return {
            "tool_use_id": tool_use_id,
            "content": f"Error executing {name}: {e}",
            "is_error": True,
        }


async def query(
    messages: list[dict[str, Any]],
    system_prompt: str,
    tools: list[Tool],
    model: str | None = None,
    cwd: str = ".",
    max_turns: int = 100,
    permission_settings: PermissionSettings | None = None,
    session_rules: PermissionRuleSet | None = None,
    on_permission_request: Callable | None = None,
    abort_event: asyncio.Event | None = None,
    default_model: str | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    turn_count = 0
    total_tool_use_count = 0
    start_time = time.monotonic()
    current_messages = list(messages)

    tool_api_params = [tool_to_api_param(t) for t in tools if t.is_enabled()]

    while turn_count < max_turns:
        if abort_event and abort_event.is_set():
            yield {"type": "aborted", "reason": "Abort signal received"}
            break

        turn_count += 1
        stream_events: list[dict[str, Any]] = []
        assistant_content: list[ContentBlock] = []
        stop_reason = ""

        gen = stream_message_with_retry(StreamRequestParams(
            messages=current_messages,
            model=model,
            system=system_prompt,
            tools=tool_api_params or None,
            abort_event=abort_event,
        ))

        stream_result = None
        try:
            while True:
                event = await gen.__anext__()
                event_dict = event.model_dump()
                stream_events.append(event_dict)
                yield event_dict
        except StopAsyncIteration as e:
            stream_result = e.value if hasattr(e, "value") else None

        if stream_result is None:
            yield {"type": "error", "error": "Stream ended without result"}
            break

        assistant_content = stream_result.assistant_message.content
        stop_reason = stream_result.stop_reason

        current_messages.append({
            "role": "assistant",
            "content": [b.model_dump() for b in assistant_content],
        })

        tool_use_blocks = [b for b in assistant_content if isinstance(b, ToolUseBlock)]

        if not tool_use_blocks:
            from ..utils.paths import get_harness_root
            harness_root = get_harness_root(cwd)
            exit_error = None
            if harness_root:
                from ..state.task_store import check_exit_gate
                exit_error = await check_exit_gate(str(harness_root))
                
            if exit_error:
                current_messages.append({"role": "user", "content": exit_error})
                continue

            duration_ms = int((time.monotonic() - start_time) * 1000)
            yield {
                "type": "result",
                "turn_count": turn_count,
                "total_tool_use_count": total_tool_use_count,
                "total_duration_ms": duration_ms,
                "stop_reason": stop_reason,
                "assistant_message": stream_result.assistant_message.model_dump(),
                "usage": stream_result.usage.model_dump(),
            }
            return

        tool_calls = [
            {"name": b.name, "input": b.input, "id": b.id}
            for b in tool_use_blocks
        ]
        total_tool_use_count += len(tool_calls)

        yield {
            "type": "tool_execution_start",
            "tool_calls": [{"name": tc["name"], "id": tc["id"]} for tc in tool_calls],
        }

        context = ToolContext(
            cwd=cwd,
            abort_event=abort_event,
            default_model=default_model or model,
            session_id=session_id,
            permission_settings=permission_settings,
            session_permission_rules=session_rules,
            on_permission_request=on_permission_request,
        )

        tool_results = await run_tools(
            tool_calls,
            tools,
            context,
            permission_settings=permission_settings,
            session_rules=session_rules,
            on_permission_request=on_permission_request,
        )

        yield {
            "type": "tool_execution_done",
            "results": tool_results,
        }

        tool_result_content: list[dict[str, Any]] = []
        for tr in tool_results:
            tool_result_content.append({
                "type": "tool_result",
                "tool_use_id": tr["tool_use_id"],
                "content": tr["content"],
                "is_error": tr.get("is_error", False),
            })

        current_messages.append({"role": "user", "content": tool_result_content})

    duration_ms = int((time.monotonic() - start_time) * 1000)
    yield {
        "type": "max_turns_reached",
        "turn_count": turn_count,
        "total_tool_use_count": total_tool_use_count,
        "total_duration_ms": duration_ms,
    }
