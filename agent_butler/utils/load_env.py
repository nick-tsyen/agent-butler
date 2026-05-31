from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv


def _read_json_env(file_path: str) -> dict[str, str]:
    try:
        raw = Path(file_path).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        env = parsed.get("env")
        if isinstance(env, dict):
            return env
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def load_env() -> None:
    home = os.environ.get("HOME", "~")

    global_config_env = _read_json_env(str(Path(home) / ".claude.json"))
    os.environ.update(global_config_env)

    settings_env = _read_json_env(str(Path(home) / ".claude" / "settings.json"))
    os.environ.update(settings_env)

    load_dotenv(override=True)
