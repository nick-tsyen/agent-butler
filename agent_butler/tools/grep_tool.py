from __future__ import annotations

import asyncio
import shutil
from typing import Any

from .base import Tool
from .path_utils import resolve_workspace_path
from ..types.tool import ToolContext, ToolResult


class GrepTool(Tool):
    @property
    def name(self) -> str:
        return "Grep"

    @property
    def description(self) -> str:
        return "Search file contents by regex pattern. Prefer this over Bash for code search."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "path": {"type": "string", "description": "Directory or file path to search within"},
                "include": {"type": "string", "description": "Optional glob filter, e.g. *.ts"},
            },
            "required": ["pattern"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        pattern = input_data.get("pattern")
        if not pattern:
            return ToolResult(content="Error: pattern is required", is_error=True)

        try:
            target_path = resolve_workspace_path(input_data.get("path", "."), context.cwd)
        except ValueError as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

        include = input_data.get("include")

        try:
            if shutil.which("rg"):
                args = ["-n", "--hidden"]
                if include:
                    args.extend(["-g", include])
                args.extend([pattern, target_path])
                proc = await asyncio.create_subprocess_exec(
                    "rg", *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                output = stdout.decode("utf-8", errors="replace").strip()
                return ToolResult(content=output if output else f"No matches found for pattern: {pattern}")

            args = ["-RIn", pattern, target_path]
            proc = await asyncio.create_subprocess_exec(
                "grep", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode("utf-8", errors="replace").strip()
            return ToolResult(content=output if output else f"No matches found for pattern: {pattern}")
        except Exception as e:
            msg = str(e)
            if "code 1" in msg:
                return ToolResult(content=f"No matches found for pattern: {pattern}")
            return ToolResult(content=f"Error running grep search: {msg}", is_error=True)

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return True


grep_tool = GrepTool()
