from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.task import TASK_STATUSES
from ..types.tool import ToolContext, ToolResult

UPDATE_STATUSES = set(TASK_STATUSES) | {"deleted"}


class TaskUpdateTool(Tool):
    @property
    def name(self) -> str:
        return "TaskUpdate"

    @property
    def description(self) -> str:
        return (
            "Update a task in the persistent task graph. Use this to mark progress, "
            "edit fields, add dependencies, or delete tasks by setting status to 'deleted'."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The id of the task to update."},
                "subject": {"type": "string", "description": "New subject."},
                "description": {"type": "string", "description": "New description."},
                "activeForm": {"type": "string", "description": "Present-continuous form for spinner."},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "deleted"]},
                "addBlocks": {"type": "array", "items": {"type": "string"}},
                "addBlockedBy": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object", "description": "Metadata keys to merge."},
            },
            "required": ["taskId"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        task_id = str(input_data.get("taskId", "")).strip()
        if not task_id:
            return ToolResult(content="Error: `taskId` is required.", is_error=True)

        from ..state.task_store import block_task, delete_task, get_task, get_task_list_id, update_task
        task_list_id = get_task_list_id(context.session_id or "default")
        existing = await get_task(task_list_id, task_id)
        if not existing:
            return ToolResult(content=f"Task #{task_id} not found", is_error=True)

        raw_status = input_data.get("status")
        if raw_status is not None and raw_status not in UPDATE_STATUSES:
            return ToolResult(content=f"Error: invalid status '{raw_status}'.", is_error=True)

        if raw_status == "deleted":
            ok = await delete_task(task_list_id, task_id)
            return (
                ToolResult(content=f"Task #{task_id} deleted.")
                if ok
                else ToolResult(content=f"Failed to delete task #{task_id}.", is_error=True)
            )

        updates: dict[str, Any] = {}
        updated_fields: list[str] = []

        for field in ("subject", "description", "activeForm"):
            snake = "active_form" if field == "activeForm" else field
            val = input_data.get(field)
            if val is not None and val != existing.get(snake):
                updates[snake] = val
                updated_fields.append(field)

        if raw_status is not None and raw_status != existing.get("status"):
            updates["status"] = raw_status
            updated_fields.append("status")

        meta = input_data.get("metadata")
        if isinstance(meta, dict):
            merged = dict(existing.get("metadata") or {})
            for k, v in meta.items():
                if v is None:
                    merged.pop(k, None)
                else:
                    merged[k] = v
            updates["metadata"] = merged
            updated_fields.append("metadata")

        if updates:
            await update_task(task_list_id, task_id, updates)

        add_blocks = input_data.get("addBlocks")
        if isinstance(add_blocks, list):
            for downstream_id in add_blocks:
                if downstream_id not in existing.get("blocks", []):
                    ok = await block_task(task_list_id, task_id, downstream_id)
                    if ok and "blocks" not in updated_fields:
                        updated_fields.append("blocks")

        add_blocked_by = input_data.get("addBlockedBy")
        if isinstance(add_blocked_by, list):
            for upstream_id in add_blocked_by:
                if upstream_id not in existing.get("blocked_by", []):
                    ok = await block_task(task_list_id, upstream_id, task_id)
                    if ok and "blockedBy" not in updated_fields:
                        updated_fields.append("blockedBy")

        if not updated_fields:
            return ToolResult(content=f"Task #{task_id} unchanged.")
        return ToolResult(content=f"Updated task #{task_id}: {', '.join(updated_fields)}")

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        from ..state.task_mode_store import is_task_mode_enabled
        return is_task_mode_enabled()


task_update_tool = TaskUpdateTool()
