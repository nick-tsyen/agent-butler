from __future__ import annotations

from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult


class MemoryWriteTool(Tool):
    @property
    def name(self) -> str:
        return "MemoryWrite"

    @property
    def description(self) -> str:
        return (
            "Save durable project memory for future conversations. "
            "Only store information that cannot be derived directly from the current repository state."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short memory title."},
                "description": {"type": "string", "description": "One-line hook used in MEMORY.md."},
                "type": {"type": "string", "enum": ["user", "feedback", "project", "reference"], "description": "Memory type."},
                "content": {"type": "string", "description": "Full markdown memory content."},
                "file_name": {"type": "string", "description": "Optional target file name."},
            },
            "required": ["name", "description", "type", "content"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        name = str(input_data.get("name", "")).strip()
        description = str(input_data.get("description", "")).strip()
        mem_type = input_data.get("type", "")
        content = str(input_data.get("content", "")).strip()
        file_name = str(input_data.get("file_name", "")).strip() or None

        valid_types = {"user", "feedback", "project", "reference"}
        if not name or not description or not content or mem_type not in valid_types:
            return ToolResult(
                content="Error: name, description, content, and a valid memory type are required.",
                is_error=True,
            )

        from ..context.memory.memdir import write_project_memory
        result = await write_project_memory(
            cwd=context.cwd,
            name=name,
            description=description,
            type=mem_type,
            content=content,
            file_name=file_name,
        )

        action = "Updated" if result.get("updatedExisting") else "Saved"
        return ToolResult(content=f"{action} {mem_type} memory to {result['fileName']}.")

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


memory_write_tool = MemoryWriteTool()
