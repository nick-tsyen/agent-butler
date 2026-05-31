from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from ..permissions.permissions import (
    PermissionDecision,
    PermissionMode,
    PermissionSettings,
    check_permission,
    load_permission_settings,
)
from ..services.api.streaming import StreamRequestParams, stream_message_with_retry
from ..state.notification_store import pop_all_notifications
from ..state.task_mode_store import get_task_mode
from ..state.todo_store import get_todos
from ..tools.registry import find_tool_by_name, get_tools_api_params
from ..types.message import (
    AssistantMessage,
    Message,
    StreamErrorEvent,
    StreamMessageDoneEvent,
    StreamTextEvent,
    StreamToolUseInputEvent,
    StreamToolUseStartEvent,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
    UserMessage,
)
from ..types.tool import ToolContext, ToolResult
from .events import (
    UIAssistantMessage,
    UIError,
    UIEvent,
    UIPermissionRequest,
    UITextDelta,
    UIToolDone,
    UIToolResultMessage,
    UIToolStart,
    UITurnComplete,
    UIUsageUpdate,
)


@dataclass
class SessionState:
    messages: list[Message] = field(default_factory=list)
    is_loading: bool = False
    spinner_label: str = "Thinking"
    streaming_text: str = ""
    total_usage: Usage = field(default_factory=lambda: Usage(input_tokens=0, output_tokens=0))
    last_usage: Usage | None = None
    system_notice: str | None = None
    permission_mode: PermissionMode = "default"
    current_model: str = ""
    todos: list[dict[str, Any]] = field(default_factory=list)
    task_mode: str = "task"


class SessionController:
    def __init__(
        self,
        model: str,
        cwd: str | None = None,
        permission_mode: PermissionMode | None = None,
    ) -> None:
        self._model = model
        self._cwd = cwd or __import__("os").getcwd()
        self._state = SessionState(current_model=model)
        self._permission_settings: PermissionSettings | None = None
        self._abort_event = asyncio.Event()
        self._permission_resolver: asyncio.Future[PermissionDecision] | None = None
        self._tool_context = ToolContext(cwd=self._cwd)

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def model(self) -> str:
        return self._model

    @property
    def cwd(self) -> str:
        return self._cwd

    async def initialize(self) -> None:
        self._permission_settings = load_permission_settings(self._cwd)

    async def submit(self, user_text: str) -> AsyncGenerator[UIEvent, None]:
        trimmed = user_text.strip()
        if not trimmed:
            return

        if trimmed in ("/exit", "/quit", "/bye"):
            return

        self._abort_event.clear()
        self._state.is_loading = True
        self._state.spinner_label = "Thinking"
        self._state.streaming_text = ""
        self._state.system_notice = None

        notifications = pop_all_notifications()
        notification_text = ""
        if notifications:
            parts = []
            for n in notifications:
                parts.append(
                    f"<task-notification>"
                    f"<agent_type>{n.get('agent_type', 'agent')}</agent_type>"
                    f"<status>{n.get('status', 'completed')}</status>"
                    f"<description>{n.get('description', '')}</description>"
                    f"</task-notification>"
                )
            notification_text = "\n".join(parts)

        user_content = trimmed
        if notification_text:
            user_content = f"{notification_text}\n\n{trimmed}" if trimmed else notification_text

        user_msg = UserMessage(content=user_content)
        self._state.messages.append(user_msg)

        try:
            async for event in self._run_agent_loop():
                yield event
        except Exception as exc:
            yield UIError(message=str(exc))
        finally:
            self._state.is_loading = False

    async def interrupt(self) -> None:
        self._abort_event.set()
        self._state.is_loading = False

    async def _run_agent_loop(self, max_turns: int = 50) -> AsyncGenerator[UIEvent, None]:
        for turn in range(max_turns):
            if self._abort_event.is_set():
                yield UITurnComplete(reason="aborted", turn_count=turn)
                return

            api_messages = self._build_api_messages()
            tools_params = get_tools_api_params(
                self._state.permission_mode if self._state.permission_mode != "default" else None
            )

            system = self._build_system_prompt()

            params = StreamRequestParams(
                messages=api_messages,
                model=self._model,
                system=system,
                tools=tools_params if tools_params else None,
                abort_event=self._abort_event,
            )

            assistant_content: list[Any] = []
            current_text = ""
            tool_calls: list[dict[str, Any]] = []

            gen = stream_message_with_retry(params)
            try:
                while True:
                    event = await gen.__anext__()
                    if isinstance(event, StreamTextEvent):
                        current_text += event.text
                        self._state.streaming_text = current_text
                        yield UITextDelta(text=event.text)
                    elif isinstance(event, StreamToolUseStartEvent):
                        tool_calls.append({
                            "id": event.id,
                            "name": event.name,
                            "input_json": "",
                        })
                    elif isinstance(event, StreamToolUseInputEvent):
                        for tc in tool_calls:
                            if tc["id"] == event.id:
                                tc["input_json"] += event.partial_json
                                break
                    elif isinstance(event, StreamMessageDoneEvent):
                        self._state.last_usage = event.usage
                        self._state.total_usage = Usage(
                            input_tokens=self._state.total_usage.input_tokens + event.usage.input_tokens,
                            output_tokens=self._state.total_usage.output_tokens + event.usage.output_tokens,
                            cache_creation_input_tokens=(
                                (self._state.total_usage.cache_creation_input_tokens or 0)
                                + (event.usage.cache_creation_input_tokens or 0)
                            ),
                            cache_read_input_tokens=(
                                (self._state.total_usage.cache_read_input_tokens or 0)
                                + (event.usage.cache_read_input_tokens or 0)
                            ),
                        )
                    elif isinstance(event, StreamErrorEvent):
                        yield UIError(message=event.error)
                        yield UITurnComplete(reason="error", turn_count=turn + 1)
                        return
            except StopAsyncIteration:
                pass

            if self._abort_event.is_set():
                yield UITurnComplete(reason="aborted", turn_count=turn)
                return

            if current_text:
                assistant_content.append(TextBlock(text=current_text))

            if not tool_calls:
                assistant_msg = AssistantMessage(content=assistant_content if assistant_content else current_text)
                self._state.messages.append(assistant_msg)
                self._state.streaming_text = ""

                yield UIAssistantMessage(content=assistant_msg.content)
                yield UIUsageUpdate(
                    turn_input=self._state.last_usage.input_tokens if self._state.last_usage else 0,
                    turn_output=self._state.last_usage.output_tokens if self._state.last_usage else 0,
                    total_input=self._state.total_usage.input_tokens,
                    total_output=self._state.total_usage.output_tokens,
                )

                from ..utils.paths import get_harness_root
                harness_root = get_harness_root(self._cwd)
                exit_error = None
                if harness_root:
                    from ..state.task_store import check_exit_gate
                    exit_error = await check_exit_gate(str(harness_root))

                if exit_error:
                    self._state.messages.append(UserMessage(content=exit_error))
                    continue

                yield UITurnComplete(reason="end_turn", turn_count=turn + 1)
                return

            for tc in tool_calls:
                try:
                    parsed_input = json.loads(tc["input_json"]) if tc["input_json"] else {}
                except json.JSONDecodeError:
                    parsed_input = {}
                tc["parsed_input"] = parsed_input

            for tc in tool_calls:
                assistant_content.append(ToolUseBlock(
                    id=tc["id"],
                    name=tc["name"],
                    input=tc["parsed_input"],
                ))

            assistant_msg = AssistantMessage(content=assistant_content)
            self._state.messages.append(assistant_msg)

            tool_results = []
            for tc in tool_calls:
                tool = find_tool_by_name(tc["name"])
                if not tool:
                    result = ToolResult(content=f"Error: tool '{tc['name']}' not found", is_error=True)
                    yield UIToolStart(id=tc["id"], name=tc["name"], input_preview="")
                    yield UIToolDone(
                        id=tc["id"], name=tc["name"],
                        result_length=len(result.content), is_error=True,
                        error_message=result.content,
                    )
                else:
                    preview = _format_input_preview(tc["parsed_input"])
                    yield UIToolStart(id=tc["id"], name=tc["name"], input_preview=preview)

                    if self._permission_settings and self._state.permission_mode != "auto":
                        perm_response = await check_permission(
                            tool,
                            tc["parsed_input"],
                            self._cwd,
                            mode=self._state.permission_mode,
                            settings=self._permission_settings,
                        )
                        if perm_response.behavior == "deny":
                            result = ToolResult(
                                content=f"Permission denied: {perm_response.reason}",
                                is_error=True,
                            )
                        elif perm_response.behavior == "ask":
                            is_plan_exit = tc["name"] == "ExitPlanMode"
                            plan_content = None
                            if is_plan_exit:
                                from ..context.plans import read_plan
                                plan_content = read_plan()

                            yield UIPermissionRequest(
                                tool_name=tc["name"],
                                summary=perm_response.request.summary,
                                risk=perm_response.request.risk,
                                rule_hint=perm_response.request.rule_hint,
                                is_plan_exit=is_plan_exit,
                                plan_content=plan_content,
                            )
                            decision = await self._await_permission()
                            if decision in ("allow_once", "allow_always"):
                                result = await tool.call(tc["parsed_input"], self._tool_context)
                            else:
                                result = ToolResult(content="Permission denied by user", is_error=True)
                        else:
                            result = await tool.call(tc["parsed_input"], self._tool_context)
                    else:
                        result = await tool.call(tc["parsed_input"], self._tool_context)

                    yield UIToolDone(
                        id=tc["id"], name=tc["name"],
                        result_length=len(result.content) if result.content else 0,
                        is_error=bool(result.is_error),
                        error_message=result.content if result.is_error else None,
                    )

                tool_results.append(ToolResultBlock(
                    tool_use_id=tc["id"],
                    content=result.content,
                    is_error=result.is_error,
                ))

            self._state.messages.append(UserMessage(content=tool_results))
            self._state.streaming_text = ""

            yield UIToolResultMessage()

            self._state.todos = get_todos("default")
            self._state.task_mode = get_task_mode()

        yield UITurnComplete(reason="max_turns", turn_count=max_turns)

    async def _await_permission(self) -> PermissionDecision:
        loop = asyncio.get_event_loop()
        self._permission_resolver = loop.create_future()
        try:
            return await self._permission_resolver
        finally:
            self._permission_resolver = None

    def resolve_permission(self, decision: PermissionDecision) -> None:
        if self._permission_resolver and not self._permission_resolver.done():
            self._permission_resolver.set_result(decision)

    def _build_api_messages(self) -> list[dict[str, Any]]:
        api_msgs: list[dict[str, Any]] = []
        for msg in self._state.messages:
            if isinstance(msg.content, str):
                api_msgs.append({"role": msg.role, "content": msg.content})
            elif isinstance(msg.content, list):
                blocks: list[dict[str, Any]] = []
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        blocks.append({"type": "text", "text": block.text})
                    elif isinstance(block, ToolUseBlock):
                        blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                    elif isinstance(block, ToolResultBlock):
                        content = block.content if isinstance(block.content, str) else str(block.content)
                        result_block: dict[str, Any] = {
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": content,
                        }
                        if block.is_error:
                            result_block["is_error"] = True
                        blocks.append(result_block)
                api_msgs.append({"role": msg.role, "content": blocks})
        return api_msgs

    def _build_system_prompt(self) -> str:
        parts = [
            "You are an AI coding assistant. You have access to tools that let you read, write, "
            "and edit files, run shell commands, and search the codebase.",
            f"Working directory: {self._cwd}",
        ]

        from ..services.skills.budget import format_skills_system_reminder
        from ..services.skills.registry import get_model_visible_skills

        skills = get_model_visible_skills()
        skills_block = format_skills_system_reminder(skills)
        if skills_block:
            parts.append(skills_block)

        return "\n\n".join(parts)

    def clear_context(self) -> None:
        self._state.messages.clear()
        self._state.streaming_text = ""
        self._state.system_notice = None


def _format_input_preview(input_data: dict[str, Any]) -> str:
    entries = []
    for key, value in list(input_data.items())[:3]:
        if value is None:
            continue
        text = str(value) if isinstance(value, str) else str(value)
        compact = " ".join(text.split()).strip()
        entries.append(f"{key}={compact[:60]}{'...' if len(compact) > 60 else ''}")
    return ", ".join(entries) if entries else ""
