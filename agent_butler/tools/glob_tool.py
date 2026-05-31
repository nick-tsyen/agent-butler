from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .base import Tool
from .path_utils import resolve_workspace_path
from ..types.tool import ToolContext, ToolResult


class GlobTool(Tool):
    @property
    def name(self) -> str:
        return "Glob"

    @property
    def description(self) -> str:
        return "Find files by glob pattern. Prefer this over Bash for file discovery."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern to match, e.g. **/*.ts"},
                "path": {"type": "string", "description": "Base directory to search from"},
            },
            "required": ["pattern"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        pattern = input_data.get("pattern")
        if not pattern:
            return ToolResult(content="Error: pattern is required", is_error=True)

        try:
            base_path = resolve_workspace_path(input_data.get("path", "."), context.cwd)
        except ValueError as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

        try:
            p = Path(base_path)
            matches = sorted(str(m) for m in p.glob(pattern))
            output = "\n".join(matches)
            return ToolResult(
                content=f"Matched files under {base_path}:\n{output}" if output else f"No files matched {pattern}"
            )
        except Exception as e:
            return ToolResult(content=f"Error running glob search: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return True


glob_tool = GlobTool()
