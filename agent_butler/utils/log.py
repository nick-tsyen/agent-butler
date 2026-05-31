from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def debug_log(scope: str, message: str, details: dict | None = None) -> None:
    if not os.environ.get("AGENT_BUTLER_DEBUG"):
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    suffix = f" {json.dumps(details)}" if details else ""
    print(f"[agent-butler][{timestamp}][{scope}] {message}{suffix}", file=sys.stderr)


def log_warn(message: str) -> None:
    print(f"[agent-butler][warn] {message}", file=sys.stderr)
