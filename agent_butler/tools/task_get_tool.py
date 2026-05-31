from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


class TaskGetTool(Tool):
    @property
    def name(self) -> str:
        return "TaskGet"

    @property
    def description(self) -> str:
        return "Retrieve the full details of a single task by id. Always call this before TaskUpdate to read current state."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The id of the task to retrieve."},
            },
            "required": ["taskId"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        task_id = str(input_data.get("taskId", "")).strip()
        if not task_id:
            return ToolResult(content="Error: `taskId` is required.", is_error=True)

        from ..state.task_store import get_task, get_task_list_id
        task_list_id = get_task_list_id(context.session_id or "default")
        task = await get_task(task_list_id, task_id)
        if not task:
            return ToolResult(content="Task not found")

        lines = [
            f"Task #{task['id']}: {task['subject']}",
            f"Status: {task['status']}",
            f"Description: {task['description']}",
        ]
        if task.get("active_form"):
            lines.append(f"ActiveForm: {task['active_form']}")
        if task.get("blocked_by"):
            lines.append(f"Blocked by: {', '.join(f'#{id}' for id in task['blocked_by'])}")
        if task.get("blocks"):
            lines.append(f"Blocks: {', '.join(f'#{id}' for id in task['blocks'])}")

        return ToolResult(content="\n".join(lines))

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        from ..state.task_mode_store import is_task_mode_enabled
        return is_task_mode_enabled()


task_get_tool = TaskGetTool()
