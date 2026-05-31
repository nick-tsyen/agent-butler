from __future__ import annotations

import time
from typing import Any

from rich.console import Group

from .command_suggestions import CommandSuggestions
from .conversation_view import ConversationView
from .events import (
    UIPermissionRequest,
    UISystemNotice,
    UITextDelta,
    UIToolDone,
    UIToolStart,
    UIUsageUpdate,
)
from .status_bar import StatusBar
from .task_list_view import TaskListView
from .todo_list_view import TodoListView
from .tool_card import ToolCallList


class StreamingBuffer:
    def __init__(self, flush_interval: float = 0.03) -> None:
        self._buffer = ""
        self._flush_interval = flush_interval
        self._last_flush = 0.0

    def append(self, text: str) -> str | None:
        self._buffer += text
        now = time.monotonic()
        if now - self._last_flush >= self._flush_interval:
            self._last_flush = now
            chunk = self._buffer
            self._buffer = ""
            return chunk
        return None

    def flush(self) -> str | None:
        if self._buffer:
            chunk = self._buffer
            self._buffer = ""
            self._last_flush = time.monotonic()
            return chunk
        return None

    def clear(self) -> None:
        self._buffer = ""
        self._last_flush = 0.0


class TUILayout:
    def __init__(self) -> None:
        self.conversation = ConversationView()
        self.tool_calls = ToolCallList()
        self.todo_list = TodoListView()
        self.task_list = TaskListView()
        self.status_bar = StatusBar()
        self.command_suggestions = CommandSuggestions()
        self._stream_buffer = StreamingBuffer()
        self._accumulated_stream = ""

    def handle_text_delta(self, event: UITextDelta) -> None:
        chunk = self._stream_buffer.append(event.text)
        if chunk:
            self._accumulated_stream += chunk
            self.conversation.set_streaming_text(self._accumulated_stream)

    def flush_stream(self) -> None:
        chunk = self._stream_buffer.flush()
        if chunk:
            self._accumulated_stream += chunk
            self.conversation.set_streaming_text(self._accumulated_stream)

    def handle_tool_start(self, event: UIToolStart) -> None:
        self.tool_calls.add_start(event.id, event.name, event.input_preview)

    def handle_tool_done(self, event: UIToolDone) -> None:
        self.tool_calls.mark_complete(
            event.id,
            result_length=event.result_length,
            is_error=event.is_error,
            error_message=event.error_message,
            display_name=event.display_name,
            display_hint=event.display_hint,
        )

    def handle_permission_request(self, event: UIPermissionRequest) -> None:
        self.status_bar.set_permission_prompt({
            "tool_name": event.tool_name,
            "summary": event.summary,
            "risk": event.risk,
            "rule_hint": event.rule_hint,
            "is_plan_exit": event.is_plan_exit,
            "plan_content": event.plan_content,
        })

    def handle_usage_update(self, event: UIUsageUpdate) -> None:
        self.status_bar.set_usage(
            event.total_input, event.total_output, event.context_percent
        )

    def handle_system_notice(self, event: UISystemNotice) -> None:
        self.status_bar.set_notice({
            "tone": event.tone,
            "title": event.title,
            "body": event.body,
        })

    def finalize_message(self) -> None:
        self._accumulated_stream = ""
        self._stream_buffer.clear()
        self.conversation.set_streaming_text("")
        self.tool_calls.clear()

    def set_loading(self, loading: bool, label: str = "Thinking") -> None:
        self.status_bar.set_loading(loading, label)

    def set_model(self, model: str) -> None:
        self.status_bar.set_model(model)

    def set_mode(self, mode: str) -> None:
        self.status_bar.set_mode(mode)

    def clear_conversation(self) -> None:
        self.conversation.clear()
        self.tool_calls.clear()
        self._accumulated_stream = ""
        self._stream_buffer.clear()

    def render(self) -> Group:
        self.flush_stream()

        renderables: list[Any] = []

        renderables.append(self.conversation.render())

        if self.tool_calls.has_pending() or self.tool_calls._cards:
            renderables.append(self.tool_calls.render())

        todo_renderable = self.todo_list.render()
        if todo_renderable:
            renderables.append(todo_renderable)

        task_renderable = self.task_list.render()
        if task_renderable:
            renderables.append(task_renderable)

        renderables.append(self.status_bar.render())

        cmd_renderable = self.command_suggestions.render()
        if cmd_renderable:
            renderables.append(cmd_renderable)

        return Group(*renderables)
