from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


def _build_allow_rules_from_prompts(prompts: list[dict[str, str]]) -> list[str]:
    rules = []
    for p in prompts:
        tool = p.get("tool", "")
        prompt = p.get("prompt", "")
        if tool and prompt:
            if tool == "Bash":
                rules.append(f"Bash({prompt} *)")
            else:
                rules.append(tool)
    return rules


class ExitPlanModeTool(Tool):
    @property
    def name(self) -> str:
        return "ExitPlanMode"

    @property
    def description(self) -> str:
        return (
            "Exit plan mode and return to normal execution mode. "
            "You can optionally declare allowedPrompts — Bash command patterns that should be auto-approved."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Brief summary of the plan."},
                "allowedPrompts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "prompt": {"type": "string"},
                        },
                        "required": ["tool", "prompt"],
                    },
                },
                "plan": {"type": "string", "description": "User-edited plan content."},
            },
            "required": ["summary"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        current_mode = context.get_permission_mode() if context.get_permission_mode else None
        if current_mode != "plan":
            return ToolResult(content="Not currently in plan mode.", is_error=True)

        from ..context.plans import get_plan_file_path, read_plan, ensure_plans_directory
        plan_path = get_plan_file_path()
        summary = input_data.get("summary", "No summary provided.")
        allowed_prompts = input_data.get("allowedPrompts", [])
        input_plan = input_data.get("plan")

        plan_was_edited = False
        if isinstance(input_plan, str):
            await ensure_plans_directory()
            Path(plan_path).write_text(input_plan, encoding="utf-8")
            plan_was_edited = True

        plan_content = await read_plan()

        if allowed_prompts and context.add_session_allow_rules:
            rules = _build_allow_rules_from_prompts(allowed_prompts)
            context.add_session_allow_rules(rules)

        if context.set_permission_mode:
            context.set_permission_mode("default")

        lines = [
            "Plan approved by user. Full tool access restored.",
            "",
            "IMPORTANT: Immediately begin implementing the plan below.",
            "",
            f"Plan file: {plan_path}",
            "",
        ]

        if plan_content:
            header = "## Approved Plan (edited by user)" if plan_was_edited else "## Approved Plan"
            lines.extend([header, "", plan_content])
        else:
            lines.append("(No plan content found on disk)")

        if allowed_prompts:
            lines.extend(["", "Auto-approved commands for this session:"])
            for p in allowed_prompts:
                lines.append(f"- {p.get('tool', '')}: {p.get('prompt', '')}")

        return ToolResult(content="\n".join(lines))

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


exit_plan_mode_tool = ExitPlanModeTool()
