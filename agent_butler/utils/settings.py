from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class SettingsFileResult(Generic[T]):
    raw: T | None
    parse_error: str | None = None


def read_json_settings_file(file_path: str) -> SettingsFileResult[Any]:
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return SettingsFileResult(raw=None)
    except OSError as e:
        return SettingsFileResult(raw=None, parse_error=f"Failed to read {file_path}: {e}")

    try:
        parsed = json.loads(text)
        return SettingsFileResult(raw=parsed)
    except json.JSONDecodeError as e:
        return SettingsFileResult(raw=None, parse_error=f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        return SettingsFileResult(raw=None, parse_error=f"Failed to parse {file_path}: {e}")
