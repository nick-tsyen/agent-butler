from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


class TaskListTool(Tool):
    @property
    def name(self) -> str:
        return "TaskList"

    @property
    def description(self) -> str:
        return (
            "List every task in the current session's task graph. "
            "Use this before starting work to find the next unblocked task."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        from ..state.task_store import get_task_list_id, list_tasks
        task_list_id = get_task_list_id(context.session_id or "default")
        all_tasks = await list_tasks(task_list_id)
        if not all_tasks:
            return ToolResult(content="No tasks found")

        resolved_ids = {t["id"] for t in all_tasks if t["status"] == "completed"}
        sorted_tasks = sorted(all_tasks, key=lambda t: int(t["id"]))

        lines = []
        for task in sorted_tasks:
            open_blockers = [bid for bid in task.get("blocked_by", []) if bid not in resolved_ids]
            blocked = f" [blocked by {', '.join(f'#{b}' for b in open_blockers)}]" if open_blockers else ""
            lines.append(f"#{task['id']} [{task['status']}] {task['subject']}{blocked}")

        return ToolResult(content="\n".join(lines))

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        from ..state.task_mode_store import is_task_mode_enabled
        return is_task_mode_enabled()


task_list_tool = TaskListTool()
