from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool
from .path_utils import resolve_workspace_path
from ..types.tool import ToolContext, ToolResult


def _add_line_numbers(content: str, start_line: int) -> str:
    lines = content.split("\n")
    max_line = start_line + len(lines) - 1
    pad = len(str(max_line))
    return "\n".join(f"{str(start_line + i).rjust(pad)}\t{line}" for i, line in enumerate(lines))


class FileReadTool(Tool):
    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file at the specified path. "
            "Use offset and limit to read specific line ranges for large files. "
            "Output includes line numbers in cat -n format."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "The absolute or relative path to the file to read"},
                "offset": {"type": "number", "description": "The 1-indexed line number to start reading from (default: 1)"},
                "limit": {"type": "number", "description": "The number of lines to read"},
            },
            "required": ["file_path"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = input_data.get("file_path")
        if not file_path:
            return ToolResult(content="Error: file_path is required", is_error=True)

        try:
            resolved = resolve_workspace_path(file_path, context.cwd)
        except ValueError as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

        offset = input_data.get("offset", 1) or 1
        limit = input_data.get("limit")

        try:
            p = Path(resolved)
            if p.is_dir():
                entries = sorted(e.name for e in p.iterdir())
                return ToolResult(content=f"Directory listing for {file_path}:\n" + "\n".join(entries))

            raw = p.read_text(encoding="utf-8")
            all_lines = raw.split("\n")
            start_idx = max(0, offset - 1)
            end_idx = start_idx + limit if limit else len(all_lines)
            selected = all_lines[start_idx:end_idx]
            numbered = _add_line_numbers("\n".join(selected), start_idx + 1)
            range_info = (
                f" (lines {start_idx + 1}-{start_idx + len(selected)} of {len(all_lines)})"
                if start_idx > 0 or end_idx < len(all_lines)
                else f" ({len(all_lines)} lines)"
            )
            return ToolResult(content=f"{resolved}{range_info}\n{numbered}")
        except FileNotFoundError:
            return ToolResult(content=f"Error: File not found: {file_path}", is_error=True)
        except PermissionError:
            return ToolResult(content=f"Error: Permission denied: {file_path}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Error reading file: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return True


file_read_tool = FileReadTool()
