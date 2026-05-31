"""
Step 7 - Permission model (allow / ask / deny)

Goal:
- classify tool calls before execution
- auto-allow low-risk reads
- ask for writes
- deny obviously dangerous operations
"""

from __future__ import annotations

import re
from typing import Any

# ── Constant sets ─────────────────────────────────────────────────────────────

# Shell command prefixes considered safe for read-only execution.
READ_ONLY_SHELL_PREFIXES: list[str] = [
    "pwd",
    "ls",
    "cat",
    "find",
    "rg",
    "grep",
    "git status",
    "git diff",
    "git log",
]

# Shell command prefixes considered dangerous; these are always denied.
DANGEROUS_BASH_PREFIXES: list[str] = [
    "rm ",
    "sudo ",
    "git push",
    "git reset --hard",
    "shutdown",
    "reboot",
]


# ── Command classifiers ────────────────────────────────────────────────────────


def is_read_only_command(command: str = "") -> bool:
    """
    Return True when *command* matches a known read-only shell prefix.

    Whitespace is normalised before comparison so extra spaces don't matter.
    """
    normalized = re.sub(r"\s+", " ", command.strip())
    return any(
        normalized == prefix or normalized.startswith(prefix + " ")
        for prefix in READ_ONLY_SHELL_PREFIXES
    )


def is_dangerous_command(command: str = "") -> bool:
    """
    Return True when *command* starts with a known dangerous prefix.

    The comparison is case-insensitive so "RM file" is still caught.
    """
    normalized = re.sub(r"\s+", " ", command.strip()).lower()
    return any(normalized.startswith(prefix) for prefix in DANGEROUS_BASH_PREFIXES)


# ── Permission request summary ─────────────────────────────────────────────────


def summarize_permission_request(tool_name: str, input: dict[str, Any]) -> str:
    """
    Build a short human-readable summary of what the tool intends to do.

    For Bash, this is the command string.
    For other tools, this is the first three input key=value pairs.
    """
    if tool_name == "Bash":
        return f"command={input.get('command') or '<empty>'}"

    # Show the first three key=value pairs for other tools.
    pairs = [f"{k}={v}" for k, v in list(input.items())[:3]]
    return ", ".join(pairs)


# ── Core permission check ─────────────────────────────────────────────────────


def check_permission(
    *,
    tool: Any,
    input: dict[str, Any],
    mode: str = "default",
) -> dict[str, Any]:
    """
    Decide how to handle a tool call before execution.

    Returns a dict with keys:
      - behavior: "allow" | "ask" | "deny"
      - reason:   human-readable explanation
      - request:  structured summary of the request
    """
    request = {
        "tool_name": tool.name,
        "input": input,
        "summary": summarize_permission_request(tool.name, input),
    }

    # Auto mode: trust everything without asking.
    if mode == "auto":
        return {"behavior": "allow", "reason": "auto mode", "request": request}

    # Plan mode: block any write action.
    if mode == "plan" and not tool.is_read_only():
        return {
            "behavior": "deny",
            "reason": "plan mode blocks write actions",
            "request": request,
        }

    # Bash commands have special handling.
    if tool.name == "Bash":
        command: str = input.get("command", "")

        if is_dangerous_command(command):
            return {"behavior": "deny", "reason": "dangerous shell command", "request": request}

        if is_read_only_command(command):
            return {"behavior": "allow", "reason": "read-only shell command", "request": request}

        return {"behavior": "ask", "reason": "shell command may change local state", "request": request}

    # Read-only tools are always safe to run automatically.
    if tool.is_read_only():
        return {"behavior": "allow", "reason": "read-only tool", "request": request}

    # Default: ask before any write operation.
    return {"behavior": "ask", "reason": "tool writes local state", "request": request}
