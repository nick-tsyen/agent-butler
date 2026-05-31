from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult

VALID_STATUSES = {"pending", "in_progress", "completed"}


def _is_todo_item(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    content = value.get("content", "")
    active_form = value.get("activeForm", "")
    status = value.get("status", "")
    return (
        isinstance(content, str) and content.strip() != ""
        and isinstance(active_form, str) and active_form.strip() != ""
        and status in VALID_STATUSES
    )


class TodoWriteTool(Tool):
    @property
    def name(self) -> str:
        return "TodoWrite"

    @property
    def description(self) -> str:
        return (
            "Update the todo list for the current session. To be used proactively and often to track progress and pending tasks. "
            "Make sure that at least one task is in_progress at all times. "
            "Always provide both content (imperative) and activeForm (present continuous) for each task."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "The full updated todo list. Each call REPLACES the entire list.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "minLength": 1, "description": "Imperative task description."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            "activeForm": {"type": "string", "minLength": 1, "description": "Present continuous form."},
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                },
            },
            "required": ["todos"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        raw = input_data.get("todos")
        if not isinstance(raw, list):
            return ToolResult(content="Error: `todos` must be an array of TodoItem objects.", is_error=True)

        todos = []
        for i, item in enumerate(raw):
            if not _is_todo_item(item):
                return ToolResult(
                    content=f"Error: todos[{i}] is not a valid TodoItem.",
                    is_error=True,
                )
            todos.append({"content": item["content"], "status": item["status"], "activeForm": item["activeForm"]})

        session_id = context.session_id or "default"
        all_done = len(todos) > 0 and all(t["status"] == "completed" for t in todos)
        new_stored = [] if all_done else todos

        from ..state.todo_store import set_todos
        set_todos(session_id, new_stored)

        return ToolResult(
            content=(
                "Todos have been modified successfully. "
                "Ensure that you continue to use the todo list to track your progress. "
                "Please proceed with the current tasks if applicable"
            )
        )

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        from ..state.task_mode_store import is_todo_mode_enabled
        return is_todo_mode_enabled()


todo_write_tool = TodoWriteTool()
