from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .paths import get_agent_butler_home, get_stream_debug_log_path

DEBUG_STREAM = os.environ.get("AGENT_BUTLER_DEBUG_STREAM") == "1"

_cached_log_path: str | None = None


def _resolve_log_path() -> str:
    global _cached_log_path
    if _cached_log_path:
        return _cached_log_path
    try:
        Path(get_agent_butler_home()).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    _cached_log_path = get_stream_debug_log_path()
    return _cached_log_path


def write_stream_debug(kind: str, payload: object) -> None:
    if not DEBUG_STREAM:
        return
    try:
        line = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "payload": payload}) + "\n"
        with open(_resolve_log_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def is_stream_debug_enabled() -> bool:
    return DEBUG_STREAM
