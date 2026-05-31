from __future__ import annotations

import re
from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult

_SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class SkillTool(Tool):
    @property
    def name(self) -> str:
        return "Skill"

    @property
    def description(self) -> str:
        return (
            "Execute a named skill within the current conversation. "
            "Pass the skill's `name` and optional `args` string."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Name of the skill to execute."},
                "args": {"type": "string", "description": "Optional argument string."},
            },
            "required": ["skill"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        skill_name = str(input_data.get("skill", "")).strip()
        args = str(input_data.get("args", ""))

        if not skill_name or not _SKILL_NAME_RE.match(skill_name):
            return ToolResult(content=f"Error: invalid skill name. Got: {skill_name}", is_error=True)

        from ..services.skills.registry import find_skill
        skill = find_skill(skill_name)
        if not skill:
            return ToolResult(content=f'Error: skill "{skill_name}" not found.', is_error=True)

        if skill.frontmatter.disable_model_invocation:
            return ToolResult(
                content=f'Error: skill "{skill_name}" has disable-model-invocation: true.',
                is_error=True,
            )

        if skill.frontmatter.has_fork_context:
            return ToolResult(
                content=f'Error: skill "{skill_name}" declares context: fork, which is not implemented.',
                is_error=True,
            )

        if skill.frontmatter.allowed_tools and context.add_session_allow_rules:
            context.add_session_allow_rules(skill.frontmatter.allowed_tools)

        session_id = context.session_id or "unknown-session"
        dir_path = "/".join(skill.base_dir.replace("\\", "/").split("/"))
        body = skill.body
        body = body.replace("${CLAUDE_SKILL_DIR}", dir_path)
        body = body.replace("${CLAUDE_SESSION_ID}", session_id)
        body = body.replace("$ARGUMENTS", args)

        header = f"Base directory for this skill: {dir_path}\n\n"
        return ToolResult(
            content=(
                f'Loaded skill "{skill.name}" ({skill.source}). '
                f"Follow the instructions below.\n\n{header}{body}"
            )
        )

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


skill_tool = SkillTool()
