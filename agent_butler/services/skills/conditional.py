from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import activate_conditional, list_conditional_skills


def activate_conditional_skills_for_paths(
    file_paths: list[str],
    cwd: str,
) -> list[str]:
    if not file_paths:
        return []
    candidates = list_conditional_skills()
    if not candidates:
        return []

    relative_paths: list[str] = []
    cwd_path = Path(cwd)
    for p in file_paths:
        abs_p = Path(p) if Path(p).is_absolute() else cwd_path / p
        try:
            rel = abs_p.resolve().relative_to(cwd_path.resolve())
            relative_paths.append(rel.as_posix())
        except (ValueError, OSError):
            continue

    if not relative_paths:
        return []

    activated: list[str] = []
    for skill in candidates:
        patterns = skill.frontmatter.paths
        if not patterns:
            continue
        matched = False
        for rel_path in relative_paths:
            if _matches_any_pattern(rel_path, patterns):
                matched = True
                break
        if matched and activate_conditional(skill.name):
            activated.append(skill.name)

    return activated


def _matches_any_pattern(path: str, patterns: list[str]) -> bool:
    import fnmatch

    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        if fnmatch.fnmatch(path, f"{pattern}/*"):
            return True
        if fnmatch.fnmatch(path, f"{pattern}/**"):
            return True
    return False


def extract_tool_file_paths(tool_name: str, input_data: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    if tool_name in ("Read", "Write", "Edit"):
        fp = input_data.get("file_path")
        if isinstance(fp, str):
            paths.append(fp)
    elif tool_name == "Glob":
        root = input_data.get("path")
        if isinstance(root, str):
            paths.append(root)
    return paths
