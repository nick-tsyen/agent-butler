from __future__ import annotations

import re
from pathlib import Path

from ..utils.paths import get_global_agent_md_path

AGENT_MD_NAME = "AGENT.md"


def _strip_html_comments(content: str) -> str:
    return re.sub(r"<!--[\s\S]*?-->", "", content).strip()


def _read_if_exists(file_path: Path) -> str | None:
    try:
        if not file_path.is_file():
            return None
        raw = file_path.read_text(encoding="utf-8")
        stripped = _strip_html_comments(raw).strip()
        return stripped or None
    except (OSError, PermissionError):
        return None


def _get_directory_chain(cwd: str) -> list[str]:
    resolved = Path(cwd).resolve()
    chain: list[str] = []
    current = resolved

    while True:
        chain.append(str(current))
        parent = current.parent
        if parent == current:
            break
        current = parent

    chain.reverse()
    return chain


def get_agent_md_files(cwd: str) -> list[str]:
    files = [get_global_agent_md_path()]
    for directory in _get_directory_chain(cwd):
        files.append(str(Path(directory) / AGENT_MD_NAME))
    return files


def load_claude_md(cwd: str) -> str | None:
    files = get_agent_md_files(cwd)
    sections: list[str] = []

    for file_path_str in files:
        file_path = Path(file_path_str)
        content = _read_if_exists(file_path)
        if content:
            sections.append(f"# Source: {file_path}\n{content}")

    return "\n\n".join(sections) if sections else None
