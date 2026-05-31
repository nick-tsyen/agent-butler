"""
Step 3 - Tool interface + first Read tool

Goal:
- define a tiny tool contract
- register tools in one place
- implement a readable file reader with line numbers
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiofiles


# ── Tool protocol ──────────────────────────────────────────────────────────────


@runtime_checkable
class Tool(Protocol):
    """Minimal contract every tool must satisfy."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def is_read_only(self) -> bool: ...
    def is_enabled(self) -> bool: ...

    async def call(
        self,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]: ...


# ── Workspace path helpers ─────────────────────────────────────────────────────


def resolve_workspace_path(file_path: str, cwd: str) -> str:
    """
    Resolve *file_path* relative to *cwd* and guard against path traversal.

    Raises ValueError if the resolved path escapes the workspace root.
    """
    resolved = Path(os.path.abspath(os.path.join(cwd, file_path)))
    cwd_path = Path(os.path.abspath(cwd))

    try:
        # relative_to raises ValueError if resolved is not inside cwd_path.
        resolved.relative_to(cwd_path)
    except ValueError:
        raise ValueError(f"Path is outside the workspace: {file_path}")

    return str(resolved)


def add_line_numbers(text: str, start_line: int = 1) -> str:
    """
    Prepend line numbers to each line of *text*.

    Numbers are right-aligned based on the width of the last line number.
    """
    lines = text.splitlines()
    last_num = start_line + len(lines) - 1
    width = len(str(last_num))

    numbered_lines = [
        f"{start_line + i:>{width}}\t{line}" for i, line in enumerate(lines)
    ]
    return "\n".join(numbered_lines)


# ── Read tool ─────────────────────────────────────────────────────────────────


class ReadTool:
    """
    Read a file from the current workspace.

    Supports partial reads with *offset* (1-based line number) and *limit*
    (maximum number of lines to return).
    """

    name = "Read"
    description = (
        "Read a file from the current workspace. "
        "Supports partial reads with offset and limit."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "offset": {"type": "number"},
            "limit": {"type": "number"},
        },
        "required": ["file_path"],
    }

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    async def call(
        self,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        file_path: str | None = input.get("file_path")
        offset: int = int(input.get("offset") or 1)
        limit: int | None = input.get("limit")
        cwd: str = context.get("cwd", os.getcwd())

        if not file_path:
            return {"content": "Error: file_path is required", "is_error": True}

        try:
            resolved_path = resolve_workspace_path(file_path, cwd)

            async with aiofiles.open(resolved_path, encoding="utf-8") as f:
                raw = await f.read()

            all_lines = raw.splitlines()

            # Convert 1-based offset to 0-based index.
            start_index = max(0, offset - 1)
            end_index = (
                start_index + int(limit) if limit is not None else len(all_lines)
            )
            selected = all_lines[start_index:end_index]

            line_range = (
                f"{start_index + 1}-{start_index + len(selected)} / {len(all_lines)}"
            )
            content = "\n".join(
                [
                    f"File: {resolved_path}",
                    f"Lines: {line_range}",
                    add_line_numbers("\n".join(selected), start_index + 1),
                ]
            )
            return {"content": content}

        except Exception as exc:
            return {"content": f"Error reading file: {exc}", "is_error": True}


# ── Tool registry ─────────────────────────────────────────────────────────────

# Singleton instance — the registry holds references to live tool objects.
read_tool = ReadTool()

all_tools: list[ReadTool] = [read_tool]


def find_tool_by_name(name: str) -> ReadTool | None:
    """Return the first tool whose name matches *name*, or None."""
    return next((t for t in all_tools if t.name == name), None)


def get_tools_api_params() -> list[dict[str, Any]]:
    """
    Return the list of enabled tool dicts ready to be passed to the
    Anthropic Messages API as the `tools` parameter.
    """
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in all_tools
        if tool.is_enabled()
    ]
