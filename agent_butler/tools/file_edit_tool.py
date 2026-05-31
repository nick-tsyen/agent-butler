from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool
from .path_utils import resolve_workspace_path
from ..types.tool import ToolContext, ToolResult


def _normalize_quotes(value: str) -> str:
    return value.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')


def _count_occurrences(haystack: str, needle: str) -> int:
    if not needle:
        return 0
    count = 0
    idx = 0
    while True:
        found = haystack.find(needle, idx)
        if found == -1:
            return count
        count += 1
        idx = found + len(needle)


def _build_edit_preview(old_string: str, new_string: str) -> str:
    old_lines = old_string.split("\n")[:3]
    new_lines = new_string.split("\n")[:3]
    return "Preview:\n" + "\n".join(
        [f"- {l}" for l in old_lines] + [f"+ {l}" for l in new_lines]
    )


class FileEditTool(Tool):
    @property
    def name(self) -> str:
        return "Edit"

    @property
    def description(self) -> str:
        return "Find a unique string in a file, replace it, and write the updated content back."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File path to edit"},
                "old_string": {"type": "string", "description": "Existing text to replace; must match uniquely"},
                "new_string": {"type": "string", "description": "Replacement text"},
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = input_data.get("file_path")
        raw_old = input_data.get("old_string")
        raw_new = input_data.get("new_string")

        if not file_path or not isinstance(raw_old, str) or not isinstance(raw_new, str):
            return ToolResult(content="Error: file_path, old_string, and new_string are required", is_error=True)

        old_string = _normalize_quotes(raw_old)
        new_string = _normalize_quotes(raw_new)

        if not old_string:
            return ToolResult(content="Error: old_string must not be empty", is_error=True)

        try:
            resolved = resolve_workspace_path(file_path, context.cwd)
        except ValueError as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

        try:
            original = Path(resolved).read_text(encoding="utf-8")
            occurrences = _count_occurrences(original, old_string)
            if occurrences == 0:
                return ToolResult(content=f"Error: old_string not found in {resolved}", is_error=True)
            if occurrences > 1:
                return ToolResult(
                    content=f"Error: old_string matched {occurrences} times; Edit requires a unique match",
                    is_error=True,
                )

            updated = original.replace(old_string, new_string, 1)
            Path(resolved).write_text(updated, encoding="utf-8")
            return ToolResult(content=f"Updated file: {resolved}\n{_build_edit_preview(old_string, new_string)}")
        except Exception as e:
            return ToolResult(content=f"Error editing file: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


file_edit_tool = FileEditTool()
