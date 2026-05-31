from __future__ import annotations

import re
from typing import Any

from .availability import is_sandbox_runtime_ready
from .settings import ResolvedSandboxSettings
from .split_command import split_command


def matches_excluded_pattern(command: str, pattern: str) -> bool:
    if pattern.endswith(":*"):
        prefix = pattern[:-2]
        return command.startswith(prefix)
    if "*" in pattern:
        regex = "^" + ".*".join(re.escape(part) for part in pattern.split("*")) + "$"
        return bool(re.match(regex, command, re.IGNORECASE))
    return command == pattern or command.startswith(pattern + " ")


def contains_excluded_command(command: str, excluded: list[str]) -> bool:
    try:
        subcommands = split_command(command)
    except Exception:
        subcommands = [command]
    if not subcommands:
        subcommands = [command]
    return any(
        matches_excluded_pattern(sub.strip(), pattern)
        for sub in subcommands
        for pattern in excluded
        if sub.strip()
    )


def should_use_sandbox(input_data: dict[str, Any], settings: ResolvedSandboxSettings) -> bool:
    if not settings.enabled:
        return False
    if not is_sandbox_runtime_ready():
        return False
    if input_data.get("dangerouslyDisableSandbox") and settings.allow_unsandboxed_commands:
        return False
    command = input_data.get("command", "")
    if not command or not str(command).strip():
        return False
    if contains_excluded_command(str(command), settings.excluded_commands):
        return False
    return True
