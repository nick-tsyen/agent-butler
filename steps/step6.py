"""
Step 6 - Dynamic system prompt assembly

Goal:
- split prompt content into stable and runtime sections
- inject environment context on every turn
- optionally include project memory from AGENT.md
"""

from __future__ import annotations

import asyncio
import os
import platform
from pathlib import Path

import aiofiles


# ── AGENT.md reader ───────────────────────────────────────────────────────────


async def _read_agent_md(cwd: str) -> str:
    """
    Read the AGENT.md file from the workspace root, if it exists.
    Returns an empty string when the file is absent.
    """
    file_path = Path(cwd) / "AGENT.md"
    try:
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        return f"# Source: {file_path}\n{content.strip()}"
    except FileNotFoundError:
        return ""


# ── Git context helper ─────────────────────────────────────────────────────────


async def _get_git_section(cwd: str) -> str:
    """
    Return a short summary of the current git branch and status.
    Falls back gracefully when git is unavailable or cwd is not a repo.
    """
    try:
        # Run both git commands concurrently for speed.
        branch_proc, status_proc = await asyncio.gather(
            asyncio.create_subprocess_exec(
                "git", "rev-parse", "--abbrev-ref", "HEAD",
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            ),
            asyncio.create_subprocess_exec(
                "git", "status", "--short",
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            ),
        )
        branch_out, _ = await branch_proc.communicate()
        status_out, _ = await status_proc.communicate()

        branch = branch_out.decode().strip()
        status = status_out.decode().strip() or "clean"

        return f"- Git branch: {branch}\n- Git status:\n{status}"
    except Exception:
        return "- Git: not available"


# ── System prompt builder ─────────────────────────────────────────────────────


async def build_system_prompt(
    *,
    cwd: str,
    additional_instructions: str = "",
) -> str:
    """
    Assemble the full system prompt for the agent.

    The prompt has two sections:
    - SYSTEM_STATIC_CONTEXT  — stable instructions that rarely change
    - SYSTEM_DYNAMIC_CONTEXT — runtime facts injected on every turn
    """
    # Static section: persona and behavioural guidelines.
    static_section = "\n".join([
        "<SYSTEM_STATIC_CONTEXT>",
        "You are Agent Butler, a terminal-native coding assistant.",
        "Be concise, practical, and action-oriented.",
        "Prefer specialized tools before using Bash.",
        "Understand the code before changing it.",
        "</SYSTEM_STATIC_CONTEXT>",
    ])

    # Gather dynamic facts concurrently.
    git_section, agent_md = await asyncio.gather(
        _get_git_section(cwd),
        _read_agent_md(cwd),
    )

    # Build dynamic facts as a list; filter out empty strings before joining.
    dynamic_parts = [
        "<SYSTEM_DYNAMIC_CONTEXT>",
        f"- Current working directory: {cwd}",
        f"- Current date: {_now_iso()}",
        f"- OS: {platform.system()} {platform.release()} ({platform.machine()})",
        git_section,
    ]
    if additional_instructions:
        dynamic_parts.append(f"- Session instructions:\n{additional_instructions}")
    if agent_md:
        dynamic_parts.append(agent_md)
    dynamic_parts.append("</SYSTEM_DYNAMIC_CONTEXT>")

    dynamic_section = "\n\n".join(filter(None, dynamic_parts))

    return static_section + "\n\n" + dynamic_section


def _now_iso() -> str:
    """Return the current UTC datetime as an ISO 8601 string."""
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).isoformat()
