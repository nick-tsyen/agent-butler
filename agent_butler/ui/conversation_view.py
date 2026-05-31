from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text

from ..types.message import AssistantMessage, Message, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage


@dataclass
class ConversationViewState:
    messages: list[Message] = field(default_factory=list)
    streaming_text: str = ""
    max_messages: int = 100


class ConversationView:
    def __init__(self) -> None:
        self._state = ConversationViewState()

    def set_messages(self, messages: list[Message]) -> None:
        self._state.messages = list(messages[-self._state.max_messages :])

    def set_streaming_text(self, text: str) -> None:
        self._state.streaming_text = text

    def clear(self) -> None:
        self._state.messages.clear()
        self._state.streaming_text = ""

    def render(self) -> Group:
        renderables: list[Any] = []

        for msg in self._state.messages:
            rendered = self._render_message(msg)
            if rendered:
                renderables.append(rendered)

        if self._state.streaming_text:
            renderables.append(
                Text.assemble(("▎ ", "magenta"), (self._state.streaming_text, ""))
            )

        if not renderables:
            renderables.append(Text(""))

        return Group(*renderables)

    def _render_message(self, message: Message) -> Any:
        if isinstance(message, UserMessage):
            return self._render_user(message)
        if isinstance(message, AssistantMessage):
            return self._render_assistant(message)
        return None

    def _render_user(self, message: UserMessage) -> Any:
        content = message.content
        if isinstance(content, str):
            if not content:
                return None
            return Text.assemble(("❯ ", "green bold"), (content, ""))
        if isinstance(content, list):
            has_tool_results = any(
                isinstance(b, ToolResultBlock) for b in content
            )
            if has_tool_results:
                return None
            parts: list[Any] = []
            for block in content:
                if isinstance(block, TextBlock) and block.text:
                    parts.append(Text.assemble(("❯ ", "green bold"), (block.text, "")))
            if parts:
                return Group(*parts) if len(parts) > 1 else parts[0]
        return None

    def _render_assistant(self, message: AssistantMessage) -> Any:
        content = message.content
        if isinstance(content, str):
            if not content:
                return None
            return self._render_assistant_text(content)
        if isinstance(content, list):
            renderables: list[Any] = []
            for block in content:
                if isinstance(block, TextBlock) and block.text:
                    renderables.append(self._render_assistant_text(block.text))
                elif isinstance(block, ToolUseBlock):
                    result = self._find_tool_result(block.id)
                    if result:
                        renderables.append(self._render_inline_tool(block, result))
            if renderables:
                return Group(*renderables) if len(renderables) > 1 else renderables[0]
        return None

    def _render_assistant_text(self, text: str) -> Any:
        try:
            return Markdown(text)
        except Exception:
            return Text.assemble(("▎ ", "magenta"), (text, ""))

    def _find_tool_result(self, tool_use_id: str) -> ToolResultBlock | None:
        for msg in self._state.messages:
            if isinstance(msg, UserMessage) and isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, ToolResultBlock) and block.tool_use_id == tool_use_id:
                        return block
        return None

    def _render_inline_tool(self, tool_use: ToolUseBlock, result: ToolResultBlock) -> Any:
        name = tool_use.name
        is_error = bool(result.is_error)
        content_str = result.content if isinstance(result.content, str) else str(result.content)

        if is_error:
            return Text.assemble(
                ("  ✗ ", "red"),
                (name, "red"),
                (" — error", "red"),
            )
        return Text.assemble(
            ("  ✓ ", "green"),
            (name, "green"),
            (f" ({len(content_str)} chars)", "dim"),
        )
