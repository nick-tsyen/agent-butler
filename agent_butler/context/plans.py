from __future__ import annotations

import secrets
from pathlib import Path

from ..utils.paths import get_plans_root

_cached_slug: str | None = None


def _generate_slug() -> str:
    return secrets.token_hex(4)


def get_plan_slug() -> str:
    global _cached_slug
    if _cached_slug is None:
        _cached_slug = _generate_slug()
    return _cached_slug


def reset_plan_slug() -> None:
    global _cached_slug
    _cached_slug = None


def get_plans_directory() -> str:
    return get_plans_root()


def get_plan_file_path() -> str:
    return str(Path(get_plans_root()) / f"{get_plan_slug()}.md")


def ensure_plans_directory() -> None:
    Path(get_plans_root()).mkdir(parents=True, exist_ok=True)


def write_plan(content: str) -> None:
    ensure_plans_directory()
    Path(get_plan_file_path()).write_text(content, encoding="utf-8")


def read_plan() -> str | None:
    try:
        return Path(get_plan_file_path()).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def plan_exists() -> bool:
    return Path(get_plan_file_path()).is_file()
