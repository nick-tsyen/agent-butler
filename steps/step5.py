"""
Step 5 - Core tools in one teaching file

Goal:
- show the essential patterns behind Read / Write / Edit / Grep / Glob / Bash
- keep each tool short enough to learn from quickly
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

import aiofiles


# ── Shared workspace path helper ──────────────────────────────────────────────


def resolve_workspace_path(file_path: str | None, cwd: str) -> str:
    """
    Resolve *file_path* relative to *cwd*, defaulting to cwd itself when None.
    Raises ValueError if the result escapes the workspace root.
    """
    effective_path = file_path or "."
    resolved = Path(os.path.abspath(os.path.join(cwd, effective_path)))
    cwd_path = Path(os.path.abspath(cwd))

    try:
        resolved.relative_to(cwd_path)
    except ValueError:
        raise ValueError(f"Path is outside the workspace: {file_path}")

    return str(resolved)


# ── Occurrence counter (used by Edit) ─────────────────────────────────────────


def count_occurrences(text: str, pattern: str) -> int:
    """Count how many times *pattern* appears in *text* (non-overlapping)."""
    count = 0
    index = 0
    while True:
        index = text.find(pattern, index)
        if index == -1:
            return count
        count += 1
        index += len(pattern)


# ── Read tool ─────────────────────────────────────────────────────────────────


class ReadTool:
    """Read file content from the workspace."""

    name = "Read"
    description = "Read file content."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"file_path": {"type": "string"}},
        "required": ["file_path"],
    }

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        resolved = resolve_workspace_path(input.get("file_path"), cwd)
        async with aiofiles.open(resolved, encoding="utf-8") as f:
            raw = await f.read()
        return {"content": raw}


# ── Write tool ────────────────────────────────────────────────────────────────


class WriteTool:
    """Create or overwrite a file."""

    name = "Write"
    description = "Create or overwrite a file."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["file_path", "content"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        resolved = resolve_workspace_path(input.get("file_path"), cwd)
        # Ensure parent directories exist.
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(resolved, "w", encoding="utf-8") as f:
            await f.write(input.get("content", ""))
        return {"content": f"Wrote {resolved}"}


# ── Edit tool ─────────────────────────────────────────────────────────────────


class EditTool:
    """Replace one unique string inside a file."""

    name = "Edit"
    description = "Replace one unique string inside a file."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        resolved = resolve_workspace_path(input.get("file_path"), cwd)

        async with aiofiles.open(resolved, encoding="utf-8") as f:
            original = await f.read()

        old_string: str = input.get("old_string", "")
        matches = count_occurrences(original, old_string)
        if matches != 1:
            return {
                "content": f"Error: expected 1 match, got {matches}",
                "is_error": True,
            }

        updated = original.replace(old_string, input.get("new_string", ""), 1)
        async with aiofiles.open(resolved, "w", encoding="utf-8") as f:
            await f.write(updated)

        return {"content": f"Edited {resolved}"}


# ── Grep tool ─────────────────────────────────────────────────────────────────


class GrepTool:
    """Search file contents with ripgrep."""

    name = "Grep"
    description = "Search file contents with ripgrep."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
    }

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        target_path = resolve_workspace_path(input.get("path") or ".", cwd)
        pattern: str = input.get("pattern", "")

        try:
            # Run rg in a thread so it doesn't block the event loop.
            proc = await asyncio.create_subprocess_exec(
                "rg", "-n", pattern, target_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()
            return {"content": output or "No matches found"}
        except Exception:
            return {"content": "No matches found"}


# ── Glob tool ─────────────────────────────────────────────────────────────────


class GlobTool:
    """Find files by glob pattern using ripgrep --files."""

    name = "Glob"
    description = "Find files by glob pattern."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
    }

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        search_dir = resolve_workspace_path(input.get("path") or ".", cwd)
        pattern: str = input.get("pattern", "*")

        proc = await asyncio.create_subprocess_exec(
            "rg", "--files", "-g", pattern,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=search_dir,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()
        return {"content": output or "No files matched"}


# ── Bash tool ─────────────────────────────────────────────────────────────────


class BashTool:
    """Run a shell command in the workspace."""

    name = "Bash"
    description = "Run a shell command in the workspace."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(self, input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        cwd: str = context.get("cwd", os.getcwd())
        command: str = input.get("command", "")
        shell: str = os.environ.get("SHELL", "/bin/bash")

        proc = await asyncio.create_subprocess_exec(
            shell, "-lc", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=os.environ.copy(),
        )
        stdout, stderr = await proc.communicate()
        exit_code = proc.returncode or 0

        content = "\n".join(
            filter(None, [
                f"Exit code: {exit_code}",
                "STDOUT:",
                stdout.decode(),
                "STDERR:",
                stderr.decode(),
            ])
        ).strip()

        return {"content": content, "is_error": exit_code != 0}


# ── Singleton tool instances ───────────────────────────────────────────────────

read_tool = ReadTool()
write_tool = WriteTool()
edit_tool = EditTool()
grep_tool = GrepTool()
glob_tool = GlobTool()
bash_tool = BashTool()
