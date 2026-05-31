from __future__ import annotations

import os
from pathlib import Path

DIR_NAME = ".agent-butler"
SETTINGS_FILE = "settings.json"


def get_agent_butler_home() -> str:
    return str(Path.home() / DIR_NAME)


def get_agent_butler_path(*segments: str) -> str:
    return str(Path(get_agent_butler_home()).joinpath(*segments))


def get_user_settings_path() -> str:
    return get_agent_butler_path(SETTINGS_FILE)


def get_global_agent_md_path() -> str:
    return get_agent_butler_path("AGENT.md")


def get_tasks_root() -> str:
    return get_agent_butler_path("tasks")


def get_plans_root() -> str:
    return get_agent_butler_path("plans")


def get_projects_root() -> str:
    return get_agent_butler_path("projects")


def get_stream_debug_log_path() -> str:
    return get_agent_butler_path("stream-debug.log")


def get_project_agent_butler_dir(cwd: str) -> str:
    return str(Path(cwd) / DIR_NAME)


def get_project_settings_path(cwd: str) -> str:
    return str(Path(get_project_agent_butler_dir(cwd)) / SETTINGS_FILE)


def get_settings_paths(cwd: str) -> dict[str, str]:
    return {
        "user": get_user_settings_path(),
        "project": get_project_settings_path(cwd),
    }


def get_harness_root(cwd: str) -> Path | None:
    current = Path(cwd).resolve()
    while True:
        if (current / "feature_list.json").is_file() or (current / "CLAUDE.md").is_file() or (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def is_harness_workspace(cwd: str) -> bool:
    return get_harness_root(cwd) is not None

