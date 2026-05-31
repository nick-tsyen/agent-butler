from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

from .claude_md import load_claude_md

SYSTEM_PROMPT_STATIC_START = "<SYSTEM_STATIC_CONTEXT>"
SYSTEM_PROMPT_STATIC_END = "</SYSTEM_STATIC_CONTEXT>"
SYSTEM_PROMPT_DYNAMIC_START = "<SYSTEM_DYNAMIC_CONTEXT>"
SYSTEM_PROMPT_DYNAMIC_END = "</SYSTEM_DYNAMIC_CONTEXT>"


def _get_static_prompt_sections() -> list[str]:
    return [
        "You are Agent Butler, a terminal-native local coding assistant running inside the user's workspace.",
        "Operate directly, be concise, and prefer taking concrete actions with tools when useful.",
        "When solving coding tasks, first understand the relevant files, then make focused changes, then verify with the least expensive effective command.",
        "Prefer specialized tools over shell when possible: use Read for reading files, Edit for precise changes, Write for full file creation or overwrite, Grep for content search, Glob for file discovery, and Bash only when shell execution is actually needed.",
        "Treat the current working directory as the primary workspace boundary. The Agent Butler system directory at ~/.agent-butler is also available for memory and session storage; do not assume other outside paths are available.",
        "When editing code, preserve existing behavior unless the user explicitly asks for a behavior change.",
        "If a command or edit fails, explain the failure briefly and choose the next best action based on the observed result.",
        "Keep answers structured and practical. Summarize what you changed or found, and avoid unnecessary narration.",
    ]


def _get_git_context(cwd: str) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        result["git_branch"] = branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        status = subprocess.check_output(
            ["git", "status", "--short"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        result["git_status"] = status or "clean"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        log = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%h %s"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if log:
            result["git_recent_commit"] = log
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return result


def _get_runtime_environment_context(cwd: str) -> dict[str, Any]:
    git = _get_git_context(cwd)
    return {
        "cwd": cwd,
        "date": datetime.now(timezone.utc).isoformat(),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        **git,
    }


def _format_environment_context(context: dict[str, Any]) -> str:
    lines = [
        "Environment:",
        f"- Current working directory: {context['cwd']}",
        f"- Current date: {context['date']}",
        f"- Operating system: {context['os']}",
    ]
    if context.get("git_branch"):
        lines.append(f"- Git branch: {context['git_branch']}")
    if context.get("git_status"):
        lines.append(f"- Git status snapshot:\n{context['git_status']}")
    if context.get("git_recent_commit"):
        lines.append(f"- Recent commit: {context['git_recent_commit']}")
    return "\n".join(lines)


def build_system_prompt(
    cwd: str,
    model: str,
    tools: list,
    skills: list,
    agents: list,
) -> str:
    environment_context = _get_runtime_environment_context(cwd)
    agent_md_context = load_claude_md(cwd)

    static_sections = [
        SYSTEM_PROMPT_STATIC_START,
        *_get_static_prompt_sections(),
        SYSTEM_PROMPT_STATIC_END,
    ]

    dynamic_parts: list[str] = [
        SYSTEM_PROMPT_DYNAMIC_START,
        _format_environment_context(environment_context),
    ]
    if agent_md_context:
        dynamic_parts.append(f"Project memory (AGENT.md):\n{agent_md_context}")
    if skills:
        skill_names = [s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in skills]
        dynamic_parts.append(f"Available skills: {', '.join(skill_names)}")
    if agents:
        agent_names = [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in agents]
        dynamic_parts.append(f"Available agents: {', '.join(agent_names)}")
    if tools:
        tool_names = [t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in tools]
        dynamic_parts.append(f"Available tools: {', '.join(tool_names)}")

    dynamic_parts.append(SYSTEM_PROMPT_DYNAMIC_END)

    return "\n\n".join(static_sections + dynamic_parts)
