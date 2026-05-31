from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from .base import Tool
from ..types.tool import ToolContext, ToolResult

DEFAULT_TIMEOUT_MS = 120_000
MAX_OUTPUT_CHARS = 30_000

READ_ONLY_COMMANDS = {
    "ls", "cat", "grep", "rg", "find", "fd", "pwd", "which",
    "git status", "git log", "git diff", "git show",
    "head", "tail", "wc", "sed",
}


def _split_command_segments(command: str) -> list[str]:
    return [s.strip() for s in re.split(r"&&|\|\||\|", command) if s.strip()]


def is_read_only_command(command: str) -> bool:
    segments = _split_command_segments(command)
    if not segments:
        return False
    for seg in segments:
        normalized = re.sub(r"\s+", " ", seg).strip()
        if normalized in READ_ONLY_COMMANDS:
            continue
        first_two = " ".join(normalized.split(" ")[:2])
        if first_two in READ_ONLY_COMMANDS:
            continue
        first = normalized.split(" ")[0]
        if first not in READ_ONLY_COMMANDS:
            return False
    return True


def _truncate_output(value: str) -> str:
    if len(value) <= MAX_OUTPUT_CHARS:
        return value
    return f"{value[:MAX_OUTPUT_CHARS]}\n...[truncated {len(value) - MAX_OUTPUT_CHARS} chars]"


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return "Execute a shell command in the current working directory and return stdout/stderr."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "number", "description": "Timeout in milliseconds (default 120000)"},
            },
            "required": ["command"],
        }

    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult:
        command = input_data.get("command")
        if not command:
            return ToolResult(content="Error: command is required", is_error=True)

        timeout_ms = input_data.get("timeout", DEFAULT_TIMEOUT_MS)
        if not isinstance(timeout_ms, (int, float)):
            timeout_ms = DEFAULT_TIMEOUT_MS

        shell = os.environ.get("SHELL", "bash")
        try:
            proc = await asyncio.create_subprocess_exec(
                shell, "-lc", command,
                cwd=context.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_ms / 1000
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(content=f"Command timed out after {timeout_ms}ms", is_error=True)

            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            code = proc.returncode or 0

            output_lines = [
                f"Command: {command}",
                f"Read-only: {is_read_only_command(command)}",
                f"Exit code: {code}",
            ]
            if stdout:
                output_lines.append(f"\nSTDOUT:\n{_truncate_output(stdout)}")
            if stderr:
                output_lines.append(f"\nSTDERR:\n{_truncate_output(stderr)}")

            return ToolResult(content="\n".join(output_lines), is_error=code != 0)
        except Exception as e:
            return ToolResult(content=f"Failed to start command: {e}", is_error=True)

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True


bash_tool = BashTool()
