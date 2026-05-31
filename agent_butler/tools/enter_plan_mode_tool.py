from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


class EnterPlanModeTool(Tool):
    @property
    def name(self) -> str:
        return "EnterPlanMode"

    @property
    def description(self) -> str:
        return (
            "Enter plan mode to explore the codebase with read-only tools before making changes. "
            "In plan mode, only Read, Grep, Glob, and read-only Bash commands are available."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief explanation of why plan mode is needed."},
            },
            "required": ["reason"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        current_mode = context.get_permission_mode() if context.get_permission_mode else None
        if current_mode == "plan":
            return ToolResult(content="Already in plan mode.", is_error=True)

        from ..context.plans import ensure_plans_directory, get_plan_file_path
        await ensure_plans_directory()
        plan_path = get_plan_file_path()

        if context.set_permission_mode:
            context.set_permission_mode("plan")

        return ToolResult(content="\n".join([
            "PLAN MODE ACTIVE — You are now in plan mode.",
            "",
            "Workflow:",
            "1. EXPLORE: Use Read, Grep, Glob, and read-only Bash commands.",
            "2. PLAN: Write a detailed implementation plan to the plan file.",
            "3. EXIT: Call ExitPlanMode with a summary.",
            "",
            f"Plan file: {plan_path}",
        ]))

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


enter_plan_mode_tool = EnterPlanModeTool()
