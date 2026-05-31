from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from ..tools.base import Tool
from ..tools.bash_tool import is_read_only_command
from ..utils.paths import get_settings_paths
from ..utils.settings import read_json_settings_file

PermissionBehavior = Literal["allow", "ask", "deny"]
PermissionMode = Literal["default", "plan", "auto"]
PermissionDecision = Literal["allow_once", "allow_always", "deny", "allow_clear_context", "allow_accept_edits"]


@dataclass
class PermissionRuleSet:
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


@dataclass
class PermissionSettings(PermissionRuleSet):
    mode: PermissionMode = "default"


@dataclass
class PermissionRequest:
    tool_name: str
    input: dict[str, Any]
    summary: str
    risk: str
    rule_hint: str


@dataclass
class PermissionResponse:
    behavior: PermissionBehavior
    reason: str
    request: PermissionRequest


PLAN_ALLOWED_TOOLS = {"Read", "Grep", "Glob"}

DANGEROUS_BASH_PREFIXES = [
    "rm ", "sudo ", "chmod ", "chown ", "mv ", "dd ", "mkfs",
    "shutdown", "reboot", "init 0", "init 6",
    "git push", "git reset --hard", "git clean -fd",
]

DEFAULT_PERMISSION_SETTINGS = PermissionSettings()


def _normalize_rule_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_mode(value: Any) -> PermissionMode | None:
    if value in ("default", "plan", "auto"):
        return value
    return None


def _read_permissions_from_settings(file_path: str) -> dict[str, Any]:
    result = read_json_settings_file(file_path)
    if result.parse_error:
        raise ValueError(f"Invalid JSON in permissions settings: {file_path}")
    if not result.raw:
        return {}
    raw = result.raw
    out: dict[str, Any] = {}
    if "allow" in raw:
        out["allow"] = _normalize_rule_list(raw["allow"])
    if "deny" in raw:
        out["deny"] = _normalize_rule_list(raw["deny"])
    mode = _normalize_mode(raw.get("mode"))
    if mode:
        out["mode"] = mode
    return out


def load_permission_settings(cwd: str) -> PermissionSettings:
    paths = get_settings_paths(cwd)
    try:
        user = _read_permissions_from_settings(paths["user"])
    except ValueError:
        user = {}
    try:
        project = _read_permissions_from_settings(paths["project"])
    except ValueError:
        project = {}

    return PermissionSettings(
        allow=[*DEFAULT_PERMISSION_SETTINGS.allow, *(user.get("allow", [])), *(project.get("allow", []))],
        deny=[*DEFAULT_PERMISSION_SETTINGS.deny, *(user.get("deny", [])), *(project.get("deny", []))],
        mode=project.get("mode") or user.get("mode") or DEFAULT_PERMISSION_SETTINGS.mode,
    )


def _escape_regex(value: str) -> str:
    return re.sub(r"[.*+?^${}()|[\]\\]", r"\\\g<0>", value)


def _wildcard_to_regex(pattern: str) -> re.Pattern[str]:
    source = ".*".join(_escape_regex(part) for part in pattern.split("*"))
    return re.compile(f"^{source}$", re.IGNORECASE)


def _extract_bash_command(input_data: dict[str, Any]) -> str:
    cmd = input_data.get("command")
    return cmd.strip() if isinstance(cmd, str) else ""


def _extract_skill_name(input_data: dict[str, Any]) -> str:
    skill = input_data.get("skill")
    return skill.strip() if isinstance(skill, str) else ""


def matches_permission_rule(rule: str, tool_name: str, input_data: dict[str, Any]) -> bool:
    normalized = rule.strip()
    if not normalized:
        return False
    if normalized == tool_name:
        return True

    if normalized.startswith("mcp__") and "*" in normalized:
        return bool(_wildcard_to_regex(normalized).match(tool_name))

    match = re.match(r"^([A-Za-z]+)\((.*)\)$", normalized)
    if not match:
        return False

    rule_tool_name, pattern = match.group(1), match.group(2)
    if rule_tool_name != tool_name:
        return False

    if tool_name == "Bash":
        command = _extract_bash_command(input_data)
        return bool(_wildcard_to_regex(pattern.strip()).match(command))

    if tool_name == "Skill":
        skill_name = _extract_skill_name(input_data)
        if not skill_name:
            return False
        trimmed = pattern.strip()
        if "*" in trimmed:
            return bool(_wildcard_to_regex(trimmed).match(skill_name))
        return trimmed == skill_name

    return False


def _matches_any_rule(rules: list[str], tool_name: str, input_data: dict[str, Any]) -> bool:
    return any(matches_permission_rule(r, tool_name, input_data) for r in rules)


def _find_first_matching_rule(rules: list[str], tool_name: str, input_data: dict[str, Any]) -> str | None:
    for r in rules:
        if matches_permission_rule(r, tool_name, input_data):
            return r
    return None


def _check_sandbox_auto_allow(
    command: str,
    rules: dict[str, list[str]],
    session_rules: dict[str, list[str]],
) -> dict[str, str]:
    from ..sandbox.split_command import split_command

    all_deny = [*session_rules.get("deny", []), *rules.get("deny", [])]
    all_allow = [*session_rules.get("allow", []), *rules.get("allow", [])]

    try:
        subcommands = split_command(command)
    except Exception:
        subcommands = [command]
    if not subcommands:
        subcommands = [command]

    for sub in subcommands:
        deny_rule = _find_first_matching_rule(all_deny, "Bash", {"command": sub})
        if deny_rule:
            return {"behavior": "deny", "reason": f'subcommand "{sub}" matched deny rule "{deny_rule}"'}

    full_deny = _find_first_matching_rule(all_deny, "Bash", {"command": command})
    if full_deny:
        return {"behavior": "deny", "reason": f'command matched deny rule "{full_deny}"'}

    for sub in subcommands:
        ask_rule = _find_first_matching_rule(all_allow, "Bash", {"command": sub})
        if ask_rule is not None:
            return {"behavior": "allow", "reason": f'subcommand "{sub}" matched allow rule "{ask_rule}"'}

    return {"behavior": "allow", "reason": "auto-allowed inside sandbox (autoAllowBashIfSandboxed)"}


def _is_dangerous_bash_command(command: str) -> bool:
    normalized = re.sub(r"\s+", " ", command).strip().lower()
    if not normalized:
        return False
    return any(normalized.startswith(prefix) for prefix in DANGEROUS_BASH_PREFIXES)


def _summarize_input(input_data: dict[str, Any]) -> str:
    entries = []
    for key, value in list(input_data.items())[:3]:
        if value is None:
            continue
        text = str(value) if isinstance(value, str) else str(value)
        compact = re.sub(r"\s+", " ", text).strip()
        entries.append(f"{key}={compact[:80]}{'...' if len(compact) > 80 else ''}")
    return ", ".join(entries) if entries else "No arguments"


def summarize_permission_request(tool_name: str, input_data: dict[str, Any]) -> str:
    if tool_name == "Bash":
        command = _extract_bash_command(input_data)
        return f"command={command}" if command else "command=<empty>"
    return _summarize_input(input_data)


def build_permission_rule_hint(tool_name: str, input_data: dict[str, Any]) -> str:
    if tool_name == "Bash":
        command = _extract_bash_command(input_data)
        first_token = command.split()[0] if command.split() else ""
        return f"Bash({first_token} *)" if first_token else "Bash"
    if tool_name == "Skill":
        skill_name = _extract_skill_name(input_data)
        return f"Skill({skill_name})" if skill_name else "Skill"
    return tool_name


def _get_risk_label(tool: Tool, input_data: dict[str, Any]) -> str:
    if tool.name == "Bash":
        command = _extract_bash_command(input_data)
        if _is_dangerous_bash_command(command):
            return "High risk: destructive shell command detected"
        if is_read_only_command(command):
            return "Low risk: read-only shell command"
        return "Medium risk: shell command may change files or git state"
    if tool.is_read_only():
        return "Low risk: read-only tool"
    if tool.name in ("Write", "Edit"):
        return "Medium risk: writes files in the workspace"
    return "Medium risk: operation may change local state"


async def check_permission(
    tool: Tool,
    input_data: dict[str, Any],
    cwd: str,
    *,
    mode: PermissionMode | None = None,
    session_rules: PermissionRuleSet | None = None,
    settings: PermissionSettings | None = None,
    on_permission_request: Callable | None = None,
) -> PermissionResponse:
    if settings is None:
        settings = load_permission_settings(cwd)
    effective_mode = mode or settings.mode
    effective_session = session_rules or PermissionRuleSet()

    request = PermissionRequest(
        tool_name=tool.name,
        input=input_data,
        summary=summarize_permission_request(tool.name, input_data),
        risk=_get_risk_label(tool, input_data),
        rule_hint=build_permission_rule_hint(tool.name, input_data),
    )

    if effective_mode == "auto":
        return PermissionResponse(behavior="allow", reason="auto mode allows all operations", request=request)

    if tool.name in ("TodoWrite", "TaskCreate", "TaskUpdate", "TaskGet", "TaskList"):
        return PermissionResponse(behavior="allow", reason=f"{tool.name} writes planning-only state", request=request)

    if effective_mode == "plan":
        if tool.name in PLAN_ALLOWED_TOOLS:
            return PermissionResponse(behavior="allow", reason="read-only tool allowed in plan mode", request=request)
        if tool.name in ("EnterPlanMode", "ExitPlanMode"):
            return PermissionResponse(behavior="ask", reason="plan mode transition requires confirmation", request=request)
        if tool.name == "Bash":
            command = _extract_bash_command(input_data)
            if is_read_only_command(command):
                return PermissionResponse(behavior="allow", reason="read-only shell command allowed in plan mode", request=request)
            return PermissionResponse(behavior="deny", reason="plan mode blocks non-read-only Bash commands", request=request)
        if tool.name == "Write":
            file_path = input_data.get("file_path", "")
            from ..context.plans import get_plan_file_path
            plan_path = get_plan_file_path()
            if isinstance(file_path, str) and file_path and Path(file_path).resolve() == Path(plan_path).resolve():
                return PermissionResponse(behavior="allow", reason="writing to plan file is allowed in plan mode", request=request)
        return PermissionResponse(behavior="deny", reason=f"plan mode blocks {tool.name}", request=request)

    if tool.name == "EnterPlanMode":
        return PermissionResponse(behavior="ask", reason="entering plan mode requires confirmation", request=request)

    if tool.name == "Bash":
        command = _extract_bash_command(input_data)
        if is_read_only_command(command):
            return PermissionResponse(behavior="allow", reason="read-only shell command", request=request)
    elif tool.is_read_only():
        return PermissionResponse(behavior="allow", reason="read-only tool", request=request)

    if _matches_any_rule(effective_session.deny, tool.name, input_data) or _matches_any_rule(settings.deny, tool.name, input_data):
        return PermissionResponse(behavior="deny", reason="matched deny rule", request=request)

    if _matches_any_rule(effective_session.allow, tool.name, input_data) or _matches_any_rule(settings.allow, tool.name, input_data):
        return PermissionResponse(behavior="allow", reason="matched allow rule", request=request)

    if tool.name == "Bash":
        command = _extract_bash_command(input_data)
        from ..sandbox.settings import load_sandbox_settings
        from ..sandbox.should_use import should_use_sandbox
        try:
            sandbox_settings = load_sandbox_settings(cwd)
        except Exception:
            sandbox_settings = None
        if (
            sandbox_settings
            and sandbox_settings.enabled
            and sandbox_settings.auto_allow_bash_if_sandboxed
            and should_use_sandbox(
                {"command": command, "dangerouslyDisableSandbox": input_data.get("dangerouslyDisableSandbox") is True},
                sandbox_settings,
            )
        ):
            decision = _check_sandbox_auto_allow(
                command,
                {"allow": settings.allow, "deny": settings.deny},
                {"allow": effective_session.allow, "deny": effective_session.deny},
            )
            return PermissionResponse(behavior=decision["behavior"], reason=decision["reason"], request=request)

    if tool.name == "Bash" and _is_dangerous_bash_command(_extract_bash_command(input_data)):
        return PermissionResponse(behavior="ask", reason="dangerous shell command requires confirmation", request=request)

    return PermissionResponse(behavior="ask", reason="operation requires confirmation", request=request)
