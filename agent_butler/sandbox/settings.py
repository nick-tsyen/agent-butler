from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .availability import is_sandbox_runtime_ready
from .types import SandboxFilesystemSettings, SandboxNetworkSettings, SandboxSettings
from ..utils.paths import get_project_settings_path, get_user_settings_path
from ..utils.settings import read_json_settings_file


@dataclass
class ResolvedSandboxSettings:
    enabled: bool = False
    auto_allow_bash_if_sandboxed: bool = True
    allow_unsandboxed_commands: bool = True
    excluded_commands: list[str] = field(default_factory=list)
    filesystem: SandboxFilesystemSettings = field(default_factory=SandboxFilesystemSettings)
    network: SandboxNetworkSettings = field(default_factory=SandboxNetworkSettings)


DEFAULT_RESOLVED_SANDBOX_SETTINGS = ResolvedSandboxSettings()


def _as_string_array(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]


def _pick_filesystem(value: Any) -> SandboxFilesystemSettings:
    if not isinstance(value, dict):
        return SandboxFilesystemSettings()
    return SandboxFilesystemSettings(
        allow_write=_as_string_array(value.get("allowWrite")),
        deny_write=_as_string_array(value.get("denyWrite")),
        allow_read=_as_string_array(value.get("allowRead")),
        deny_read=_as_string_array(value.get("denyRead")),
    )


def _pick_network(value: Any) -> SandboxNetworkSettings:
    if not isinstance(value, dict):
        return SandboxNetworkSettings()
    return SandboxNetworkSettings(
        allowed_domains=_as_string_array(value.get("allowedDomains")),
        denied_domains=_as_string_array(value.get("deniedDomains")),
    )


def _pick_sandbox(value: Any) -> SandboxSettings:
    if not isinstance(value, dict):
        return SandboxSettings()
    raw = value.get("sandbox", value)
    if not isinstance(raw, dict):
        return SandboxSettings()
    return SandboxSettings(
        enabled=bool(raw.get("enabled", False)),
        auto_allow_bash_if_sandboxed=bool(raw.get("autoAllowBashIfSandboxed", True)),
        allow_unsandboxed_commands=bool(raw.get("allowUnsandboxedCommands", True)),
        excluded_commands=_as_string_array(raw.get("excludedCommands")),
        filesystem=_pick_filesystem(raw.get("filesystem")),
        network=_pick_network(raw.get("network")),
    )


def _merge_string_arrays(*lists: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result


def resolve_sandbox_settings(user: SandboxSettings, project: SandboxSettings) -> ResolvedSandboxSettings:
    return ResolvedSandboxSettings(
        enabled=project.enabled or user.enabled,
        auto_allow_bash_if_sandboxed=project.auto_allow_bash_if_sandboxed and user.auto_allow_bash_if_sandboxed,
        allow_unsandboxed_commands=project.allow_unsandboxed_commands and user.allow_unsandboxed_commands,
        excluded_commands=_merge_string_arrays(user.excluded_commands, project.excluded_commands),
        filesystem=SandboxFilesystemSettings(
            allow_write=_merge_string_arrays(user.filesystem.allow_write, project.filesystem.allow_write),
            deny_write=_merge_string_arrays(user.filesystem.deny_write, project.filesystem.deny_write),
            allow_read=_merge_string_arrays(user.filesystem.allow_read, project.filesystem.allow_read),
            deny_read=_merge_string_arrays(user.filesystem.deny_read, project.filesystem.deny_read),
        ),
        network=SandboxNetworkSettings(
            allowed_domains=_merge_string_arrays(user.network.allowed_domains, project.network.allowed_domains),
            denied_domains=_merge_string_arrays(user.network.denied_domains, project.network.denied_domains),
        ),
    )


def _read_sandbox_from_file(file_path: str) -> SandboxSettings:
    result = parse_settings_file(file_path)
    return _pick_sandbox(result)


def parse_settings_file(file_path: str) -> dict[str, Any]:
    result = read_json_settings_file(file_path)
    if result.parse_error:
        raise ValueError(f"Invalid JSON in sandbox settings: {file_path}")
    if not result.raw:
        return {}
    return result.raw if isinstance(result.raw, dict) else {}


def load_sandbox_settings(cwd: str) -> ResolvedSandboxSettings:
    user_path = get_user_settings_path()
    project_path = get_project_settings_path(cwd)

    user_raw = parse_settings_file(user_path)
    project_raw = parse_settings_file(project_path)

    user_sandbox = _pick_sandbox(user_raw)
    project_sandbox = _pick_sandbox(project_raw)

    return resolve_sandbox_settings(user_sandbox, project_sandbox)
