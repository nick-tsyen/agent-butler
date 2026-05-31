from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .settings import ResolvedSandboxSettings
from .types import SandboxFilesystemSettings, SandboxProfile
from ..utils.paths import (
    get_agent_butler_home,
    get_global_agent_md_path,
    get_project_settings_path,
    get_user_settings_path,
)

PERMISSION_RULE_RE = re.compile(r"^([A-Za-z]+)\(([^)]*)\)$")
SYSTEM_DENY_PATHS_RAW = ["/etc", "/usr", "/private/etc"]


def _canonicalize(p: str) -> str:
    try:
        return str(Path(p).resolve())
    except OSError:
        return p


def _expand_home(p: str) -> str:
    if p.startswith("~"):
        return p.replace("~", os.environ.get("HOME", ""), 1)
    return p


def _strip_glob_suffix(p: str) -> str:
    return re.sub(r"/\*+$", "", p)


def _resolve_rule_path(value: str, cwd: str) -> str:
    expanded = _expand_home(value)
    if Path(expanded).is_absolute():
        return _canonicalize(expanded)
    return _canonicalize(str(Path(cwd) / expanded))


def _parse_rule(rule: str) -> dict[str, str] | None:
    match = PERMISSION_RULE_RE.match(rule.strip())
    if not match:
        return None
    return {"tool_name": match.group(1), "rule_content": match.group(2)}


def _get_critical_deny_paths(cwd: str) -> list[str]:
    paths = [
        get_agent_butler_home(),
        get_user_settings_path(),
        get_project_settings_path(cwd),
        get_global_agent_md_path(),
    ]
    return [_canonicalize(p) for p in paths]


def build_sandbox_profile(
    cwd: str,
    settings: ResolvedSandboxSettings,
    permissions: dict[str, list[str]],
) -> SandboxProfile:
    allow_write = [_canonicalize(cwd), _canonicalize(str(Path.cwd() / ".agent-butler"))]
    deny_write = [_canonicalize(p) for p in SYSTEM_DENY_PATHS_RAW]
    deny_write.extend(_get_critical_deny_paths(cwd))

    allow_read = [_canonicalize(cwd)]
    allowed_domains: list[str] = []
    denied_domains: list[str] = []

    for p in settings.filesystem.allow_write:
        resolved = _resolve_rule_path(p, cwd)
        if resolved not in allow_write:
            allow_write.append(resolved)

    for p in settings.filesystem.deny_write:
        resolved = _resolve_rule_path(p, cwd)
        if resolved not in deny_write:
            deny_write.append(resolved)

    for p in settings.filesystem.allow_read:
        resolved = _resolve_rule_path(p, cwd)
        if resolved not in allow_read:
            allow_read.append(resolved)

    for p in settings.filesystem.deny_read:
        resolved = _resolve_rule_path(p, cwd)

    allowed_domains.extend(settings.network.allowed_domains)
    denied_domains.extend(settings.network.denied_domains)

    for rule in permissions.get("allow", []):
        parsed = _parse_rule(rule)
        if not parsed:
            continue
        if parsed["tool_name"] in ("Write", "Edit"):
            resolved = _resolve_rule_path(parsed["rule_content"], cwd)
            if resolved not in allow_write:
                allow_write.append(resolved)
        elif parsed["tool_name"] == "Read":
            resolved = _resolve_rule_path(parsed["rule_content"], cwd)
            if resolved not in allow_read:
                allow_read.append(resolved)

    for rule in permissions.get("deny", []):
        parsed = _parse_rule(rule)
        if not parsed:
            continue
        if parsed["tool_name"] in ("Write", "Edit"):
            resolved = _resolve_rule_path(parsed["rule_content"], cwd)
            if resolved not in deny_write:
                deny_write.append(resolved)

    return SandboxProfile(
        allow_write=allow_write,
        deny_write=deny_write,
        allow_read=allow_read,
        allowed_domains=allowed_domains,
        denied_domains=denied_domains,
    )
