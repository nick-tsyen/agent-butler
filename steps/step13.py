"""
Step 13 - Plan Mode

Goal:
- let the agent switch into a "look first, act later" mode
- allow only read-only exploration while planning
- store the plan in a markdown file on disk
- exit planning with an approved execution plan

This file is a teaching version that condenses the core mechanics.
"""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import Any

import aiofiles

# ── Constants ─────────────────────────────────────────────────────────────────

AGENT_BUTLER_HOME: Path = Path.home() / ".agent-butler"
PLANS_DIR: Path = AGENT_BUTLER_HOME / "plans"

# Tools allowed while in plan mode (read-only exploration).
PLAN_ALLOWED_TOOLS: frozenset[str] = frozenset(["Read", "Grep", "Glob"])

# Module-level slug — generated once per process, shared across calls.
_cached_plan_slug: str | None = None


# ── Plan slug and file path ────────────────────────────────────────────────────


def _generate_plan_slug() -> str:
    """Generate a short random hex slug for the current planning session."""
    return secrets.token_hex(4)


def get_plan_slug() -> str:
    """Return (or lazily generate) the cached plan slug for this process."""
    global _cached_plan_slug
    if _cached_plan_slug is None:
        _cached_plan_slug = _generate_plan_slug()
    return _cached_plan_slug


def get_plan_file_path() -> Path:
    """Return the on-disk path for the current plan file."""
    return PLANS_DIR / f"{get_plan_slug()}.md"


# ── Directory and I/O helpers ─────────────────────────────────────────────────


async def ensure_plans_directory() -> None:
    """Create the plans directory if it doesn't exist."""
    PLANS_DIR.mkdir(parents=True, exist_ok=True)


async def write_plan(content: str) -> Path:
    """Write *content* to the plan file and return its path."""
    await ensure_plans_directory()
    plan_path = get_plan_file_path()
    async with aiofiles.open(plan_path, "w", encoding="utf-8") as f:
        await f.write(content)
    return plan_path


async def read_plan() -> str | None:
    """Read the current plan file. Returns None if it doesn't exist yet."""
    try:
        async with aiofiles.open(get_plan_file_path(), encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError:
        return None


# ── Allow-rule builder ────────────────────────────────────────────────────────


def _build_allow_rules_from_prompts(prompts: list[dict[str, str]]) -> list[str]:
    """
    Convert a list of ``{tool, prompt}`` dicts into permission allow-rules.

    Bash rules use the ``Bash(<pattern> *)`` format; other tools are named directly.
    """
    rules = []
    for item in prompts:
        if not item.get("tool") or not item.get("prompt"):
            continue
        if item["tool"] == "Bash":
            rules.append(f"Bash({item['prompt']} *)")
        else:
            rules.append(item["tool"])
    return rules


# ── EnterPlanMode tool ────────────────────────────────────────────────────────


class EnterPlanModeTool:
    """Switch the agent into plan mode (read-only exploration)."""

    name = "EnterPlanMode"
    description = "Enter plan mode to explore with read-only tools before making changes."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"reason": {"type": "string"}},
        "required": ["reason"],
    }

    def is_read_only(self) -> bool:
        return False  # mode-switching is considered a state change

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        get_permission_mode = context.get("get_permission_mode")
        if callable(get_permission_mode) and get_permission_mode() == "plan":
            return {"content": "Already in plan mode.", "is_error": True}

        await ensure_plans_directory()
        plan_path = get_plan_file_path()

        set_permission_mode = context.get("set_permission_mode")
        if callable(set_permission_mode):
            set_permission_mode("plan")

        return {
            "content": "\n".join([
                "PLAN MODE ACTIVE — You are now in plan mode.",
                "",
                "Workflow:",
                "1. EXPLORE: Use Read, Grep, Glob, and read-only Bash commands.",
                "2. PLAN: Write the implementation plan to the plan file.",
                "3. EXIT: Call ExitPlanMode when the plan is ready.",
                "",
                "Rules:",
                "- Do not edit source files yet.",
                "- Do not run destructive shell commands.",
                "- Only the plan file may be written in plan mode.",
                "",
                f"Plan file: {plan_path}",
            ])
        }


# ── ExitPlanMode tool ─────────────────────────────────────────────────────────


class ExitPlanModeTool:
    """Exit plan mode and resume normal execution."""

    name = "ExitPlanMode"
    description = "Exit plan mode and resume normal execution."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "allowed_prompts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["tool", "prompt"],
                },
            },
            "plan": {"type": "string"},
        },
        "required": ["summary"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        get_permission_mode = context.get("get_permission_mode")
        if callable(get_permission_mode) and get_permission_mode() != "plan":
            return {"content": "Not currently in plan mode.", "is_error": True}

        plan_path = get_plan_file_path()
        allowed_prompts = input.get("allowed_prompts") or []

        # Optionally persist the plan to disk.
        if isinstance(input.get("plan"), str):
            await ensure_plans_directory()
            async with aiofiles.open(plan_path, "w", encoding="utf-8") as f:
                await f.write(input["plan"])

        # Register any approved allow-rules for this session.
        if allowed_prompts:
            allow_rules = _build_allow_rules_from_prompts(allowed_prompts)
            add_session_allow_rules = context.get("add_session_allow_rules")
            if callable(add_session_allow_rules):
                add_session_allow_rules(allow_rules)

        set_permission_mode = context.get("set_permission_mode")
        if callable(set_permission_mode):
            set_permission_mode("default")

        plan_content = await read_plan()
        return {
            "content": "\n".join([
                "Plan approved by user. Full tool access restored.",
                "",
                "IMPORTANT: Start implementing immediately.",
                "Do not summarize the plan again.",
                "",
                f"Plan file: {plan_path}",
                "",
                plan_content or "(No plan content found)",
            ])
        }


# ── Permission checks ─────────────────────────────────────────────────────────


def is_read_only_command(command: str | None) -> bool:
    """Return True when *command* matches a known read-only shell prefix."""
    normalized = re.sub(r"\s+", " ", str(command or "").strip())
    prefixes = ["pwd", "ls", "cat", "find", "rg", "grep", "git status", "git diff", "git log"]
    return any(
        normalized == prefix or normalized.startswith(prefix + " ")
        for prefix in prefixes
    )


def check_permission_in_plan_mode(
    *, tool_name: str, input: dict[str, Any]
) -> dict[str, str]:
    """
    Classify a tool call while the agent is in plan mode.

    Returns a dict with ``behavior`` and ``reason`` keys.
    """
    if tool_name in PLAN_ALLOWED_TOOLS:
        return {"behavior": "allow", "reason": "read-only tool allowed in plan mode"}

    if tool_name in ("EnterPlanMode", "ExitPlanMode"):
        return {"behavior": "ask", "reason": "plan mode transition requires confirmation"}

    if tool_name == "Bash":
        if is_read_only_command(input.get("command")):
            return {"behavior": "allow", "reason": "read-only shell command allowed"}
        return {"behavior": "deny", "reason": "plan mode blocks non-read-only Bash commands"}

    if tool_name == "Write":
        requested_path = input.get("file_path", "")
        if isinstance(requested_path, str):
            resolved = str(Path(requested_path).resolve())
            if resolved == str(get_plan_file_path().resolve()):
                return {"behavior": "allow", "reason": "writing to the plan file is allowed"}

    return {"behavior": "deny", "reason": f"plan mode blocks {tool_name}"}


def get_tools_api_params(
    mode: str, all_tools: list[Any]
) -> list[Any]:
    """
    Filter the tool list based on the current mode.

    In plan mode, EnterPlanMode is hidden (already active).
    Otherwise, ExitPlanMode is hidden (not yet in plan mode).
    """
    if mode == "plan":
        return [t for t in all_tools if t.name != "EnterPlanMode"]
    return [t for t in all_tools if t.name != "ExitPlanMode"]


def get_plan_mode_attachment(plan_file_path: str | Path) -> dict[str, Any]:
    """Return a user message reminding the model it is in plan mode."""
    return {
        "role": "user",
        "content": "\n".join([
            "[plan_mode_attachment]",
            "PLAN MODE ACTIVE — Only read-only tools are available.",
            f"Write your plan to: {plan_file_path}",
            "Call ExitPlanMode when your plan is ready.",
        ]),
    }


# ── Singleton tool instances ───────────────────────────────────────────────────

enter_plan_mode_tool = EnterPlanModeTool()
exit_plan_mode_tool = ExitPlanModeTool()
