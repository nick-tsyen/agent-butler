"""
Step 8 - QueryEngine for multi-turn orchestration

Goal:
- keep session state outside the UI
- rebuild the system prompt each turn
- accumulate token usage across the whole session
- handle slash commands in one place
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from .step4 import query
from .step6 import build_system_prompt


def _empty_usage() -> dict[str, int]:
    """Return a zeroed usage dict."""
    return {"input_tokens": 0, "output_tokens": 0}


class QueryEngine:
    """
    Stateful multi-turn query engine.

    Encapsulates conversation history, cumulative token usage, model
    selection, and slash-command handling so the UI layer stays thin.
    """

    def __init__(
        self,
        *,
        model: str,
        tool_context: dict[str, Any],
        permission_mode: str = "default",
    ) -> None:
        # Conversation history — list of user/assistant messages.
        self.messages: list[dict[str, Any]] = []
        # Running token totals across all turns in this session.
        self.total_usage: dict[str, int] = _empty_usage()
        self.default_model: str = model
        # Per-session model override set by /model <name>.
        self.session_model_override: str | None = None
        self.tool_context: dict[str, Any] = tool_context
        self.permission_mode: str = permission_mode
        # Cancellation is signalled via asyncio.Event in a real implementation;
        # this simple flag is sufficient for teaching purposes.
        self._abort: bool = False

    def get_active_model(self) -> str:
        """Return the currently active model (session override takes precedence)."""
        return self.session_model_override or self.default_model

    def interrupt(self) -> bool:
        """
        Request cancellation of the current in-flight query.

        Returns True if there was an active query to cancel.
        """
        if not self._abort:
            self._abort = True
            return True
        return False

    async def submit_message(self, input: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a user message or slash command and yield stream events.

        Slash commands are handled synchronously; regular messages start an
        agentic loop that yields low-level stream events plus higher-level
        messages_updated / usage_updated events.
        """
        return self._submit_message_impl(input)

    async def _submit_message_impl(self, input: str) -> AsyncGenerator[dict[str, Any], None]:
        text = input.strip()
        if not text:
            return  # ignore blank input

        # Dispatch slash commands before hitting the API.
        if text.startswith("/"):
            async for event in self._handle_command(text):
                yield event
            return

        # Append the user message and notify the UI.
        user_message: dict[str, Any] = {"role": "user", "content": text}
        self.messages.append(user_message)
        yield {"type": "messages_updated", "messages": list(self.messages)}

        self._abort = False  # reset abort flag for this query

        # Rebuild the system prompt on each turn so it reflects current state.
        system_prompt = await build_system_prompt(cwd=self.tool_context.get("cwd", "."))

        gen = query(
            messages=list(self.messages),
            model=self.get_active_model(),
            system_prompt=system_prompt,
            tool_context={**self.tool_context},
        )

        async for event in await gen:
            if self._abort:
                break

            yield event

            # Mirror assistant and tool-result messages into local history.
            if event.get("type") in ("assistant_message", "tool_result_message"):
                self.messages.append(event["message"])
                yield {"type": "messages_updated", "messages": list(self.messages)}

            elif event.get("type") == "query_done":
                # Final event: accumulate usage and sync messages from final state.
                state_messages = event.get("state", {}).get("messages")
                if state_messages is not None:
                    self.messages = list(state_messages)
                turn_usage: dict[str, int] = event.get("usage", _empty_usage())
                self.total_usage["input_tokens"] += turn_usage.get("input_tokens", 0)
                self.total_usage["output_tokens"] += turn_usage.get("output_tokens", 0)
                yield {"type": "usage_updated", "total_usage": dict(self.total_usage)}

    async def _handle_command(self, command: str) -> AsyncGenerator[dict[str, Any], None]:
        """Handle a slash command and yield zero or more command events."""

        if command == "/clear":
            self.messages.clear()
            yield {"type": "messages_updated", "messages": []}
            yield {"type": "command", "kind": "info", "message": "Conversation cleared."}
            return

        if command == "/cost":
            msg = (
                f"Input={self.total_usage['input_tokens']}, "
                f"Output={self.total_usage['output_tokens']}"
            )
            yield {"type": "command", "kind": "info", "message": msg}
            return

        if command.startswith("/model "):
            next_model = command[len("/model "):].strip()
            self.session_model_override = next_model or None
            yield {
                "type": "command",
                "kind": "info",
                "message": f"Active model: {self.get_active_model()}",
            }
            return

        if command == "/help":
            yield {
                "type": "command",
                "kind": "info",
                "message": "Commands: /help /clear /cost /model <name>",
            }
            return

        # Unknown command.
        yield {"type": "command", "kind": "error", "message": f"Unknown command: {command}"}
