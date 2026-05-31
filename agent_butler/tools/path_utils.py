from __future__ import annotations

import os
from pathlib import Path

from ..utils.paths import get_agent_butler_home


def get_tool_allowed_roots(cwd: str) -> list[str]:
    return [str(Path(cwd).resolve()), str(Path(get_agent_butler_home()).resolve())]


def describe_allowed_roots(cwd: str) -> str:
    return ", ".join(get_tool_allowed_roots(cwd))


def expand_home(file_path: str) -> str:
    if file_path.startswith("~"):
        return file_path.replace("~", os.environ.get("HOME", ""), 1)
    return file_path


def resolve_safe_path(file_path: str, cwd: str) -> str:
    return str(Path(cwd) / expand_home(file_path))


def ensure_inside_allowed_roots(resolved_path: str, cwd: str) -> None:
    normalized = Path(resolved_path).resolve()
    for root in get_tool_allowed_roots(cwd):
        try:
            normalized.relative_to(root)
            return
        except ValueError:
            continue
    raise ValueError(
        f"Path is outside the allowed roots: {resolved_path}. Allowed roots: {describe_allowed_roots(cwd)}"
    )


def resolve_workspace_path(file_path: str, cwd: str) -> str:
    resolved = resolve_safe_path(file_path, cwd)
    ensure_inside_allowed_roots(resolved, cwd)
    return resolved
