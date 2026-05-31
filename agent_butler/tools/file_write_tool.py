from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool
from .path_utils import resolve_workspace_path
from ..types.tool import ToolContext, ToolResult


class FileWriteTool(Tool):
    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return "Create a file or overwrite an existing file with the provided content."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Full file content to write"},
            },
            "required": ["file_path", "content"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = input_data.get("file_path")
        content = input_data.get("content")

        if not file_path:
            return ToolResult(content="Error: file_path is required", is_error=True)
        if not isinstance(content, str):
            return ToolResult(content="Error: content must be a string", is_error=True)

        try:
            resolved = resolve_workspace_path(file_path, context.cwd)
        except ValueError as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

        try:
            p = Path(resolved)
            existed = p.exists()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            action = "Updated" if existed else "Created"
            return ToolResult(content=f"{action} file: {resolved} ({len(content)} chars)")
        except Exception as e:
            return ToolResult(content=f"Error writing file: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


file_write_tool = FileWriteTool()
