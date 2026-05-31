from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

from .paths import get_projects_root


def _encode_session_dir(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", session_id)


def get_task_output_path(session_id: str, agent_id: str) -> str:
    return str(
        Path(get_projects_root())
        / _encode_session_dir(session_id)
        / "tasks"
        / f"{agent_id}.output"
    )


async def ensure_task_output_file(session_id: str, agent_id: str) -> str:
    file_path = get_task_output_path(session_id, agent_id)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(file_path).touch(exist_ok=True)
    return file_path


TaskOutputEvent = Union[
    dict[str, Any],
]


async def append_task_output(file_path: str, event: dict[str, Any]) -> None:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def preview_tool_result(content: str, max_len: int = 2000) -> str:
    if len(content) <= max_len:
        return content
    return f"{content[:max_len]}\n... [truncated {len(content) - max_len} chars]"
