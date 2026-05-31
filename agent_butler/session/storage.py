from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..utils.paths import get_projects_root


def _encode_session_dir(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", session_id)


def _session_dir(session_id: str) -> Path:
    return Path(get_projects_root()) / _encode_session_dir(session_id)


def _session_file(session_id: str) -> Path:
    return _session_dir(session_id) / "messages.jsonl"


async def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    d = _session_dir(session_id)
    d.mkdir(parents=True, exist_ok=True)
    path = _session_file(session_id)
    with path.open("w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")


async def load_session(session_id: str) -> list[dict[str, Any]] | None:
    path = _session_file(session_id)
    if not path.is_file():
        return None
    messages: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        return None
    return messages


async def list_sessions() -> list[str]:
    root = Path(get_projects_root())
    if not root.is_dir():
        return []
    sessions: list[str] = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "messages.jsonl").is_file():
            sessions.append(d.name)
    return sessions
