from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


class TaskCreateTool(Tool):
    @property
    def name(self) -> str:
        return "TaskCreate"

    @property
    def description(self) -> str:
        return (
            "Create a structured task for the current session's persistent task graph. "
            "Tasks survive restarts and /clear, and support dependencies via blocks/blockedBy."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Imperative one-line title."},
                "description": {"type": "string", "description": "What needs to be done."},
                "activeForm": {"type": "string", "description": "Present-continuous form for spinner."},
                "metadata": {"type": "object", "description": "Free-form metadata."},
            },
            "required": ["subject", "description"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        subject = str(input_data.get("subject", "")).strip()
        description = str(input_data.get("description", "")).strip()
        active_form = str(input_data.get("activeForm", "")).strip() or None
        metadata = input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else None

        if not subject:
            return ToolResult(content="Error: `subject` must be a non-empty string.", is_error=True)
        if not description:
            return ToolResult(content="Error: `description` must be a non-empty string.", is_error=True)

        from ..state.task_store import create_task, get_task_list_id
        task_list_id = get_task_list_id(context.session_id or "default")
        task_id = await create_task(task_list_id, {
            "subject": subject,
            "description": description,
            "active_form": active_form,
            "status": "pending",
            "blocks": [],
            "blocked_by": [],
            "metadata": metadata,
        })

        return ToolResult(content=f"Task #{task_id} created: {subject}")

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        from ..state.task_mode_store import is_task_mode_enabled
        return is_task_mode_enabled()


task_create_tool = TaskCreateTool()
