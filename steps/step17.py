"""
Step 17 - Skills system

Goal:
- load skill definition files from disk
- inject the active skill's content into the system prompt
- provide a tool that lets the model switch skills mid-session
- keep the registry small enough to read in one sitting

A Skill is a markdown file with YAML frontmatter:

  ---
  name: MySkill
  description: Short one-liner for tool list
  ---

  … markdown instructions the model can follow …
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import aiofiles

# ── Config ────────────────────────────────────────────────────────────────────

# Directories searched for skill files, in priority order.
SKILL_SEARCH_DIRS: list[Path] = [
    Path.home() / ".agent-butler" / "skills",       # user-global skills
    Path.home() / ".config" / "agent-butler" / "skills",  # XDG config
]

MAX_SKILL_CONTENT_TOKENS: int = 10_000  # rough limit for the injected block
CHARS_PER_TOKEN: int = 4  # 4 chars ≈ 1 token


# ── Frontmatter parser ────────────────────────────────────────────────────────


def parse_skill_frontmatter(content: str) -> dict[str, Any] | None:
    """
    Parse a skill markdown file's YAML frontmatter.

    Returns a dict with ``name``, ``description``, and ``body`` keys,
    or None if the frontmatter is missing or incomplete.
    """
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$", content)
    if not match:
        return None

    raw_header = match.group(1)
    body = match.group(2).strip()
    fields: dict[str, str] = {}

    for line in raw_header.splitlines():
        idx = line.find(":")
        if idx == -1:
            continue
        key = line[:idx].strip()
        value = line[idx + 1:].strip()
        if key and value:
            fields[key] = value

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name or not description:
        return None

    return {"name": name, "description": description, "body": body}


# ── File discovery ────────────────────────────────────────────────────────────


async def _read_skill_file(path: Path) -> dict[str, Any] | None:
    """Read and parse a single skill file. Returns None if invalid."""
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            raw = await f.read()
        parsed = parse_skill_frontmatter(raw)
        if parsed is None:
            return None
        return {**parsed, "file_path": str(path)}
    except Exception:
        return None


async def discover_skills(extra_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    """
    Discover all valid skill files across the configured search directories.

    Files are deduplicated by ``name``; the first directory wins.
    """
    search_dirs = [*(extra_dirs or []), *SKILL_SEARCH_DIRS]
    seen_names: set[str] = set()
    skills: list[dict[str, Any]] = []

    for directory in search_dirs:
        if not directory.exists() or not directory.is_dir():
            continue
        md_files = list(directory.glob("*.md"))
        # Load all skill files from this directory concurrently.
        loaded = await asyncio.gather(*[_read_skill_file(f) for f in md_files])
        for skill in loaded:
            if skill is None:
                continue
            if skill["name"] in seen_names:
                continue  # first directory wins for duplicate names
            seen_names.add(skill["name"])
            skills.append(skill)

    return skills


# ── Registry ──────────────────────────────────────────────────────────────────

_skill_registry: list[dict[str, Any]] = []
_active_skill: dict[str, Any] | None = None


def get_skill_registry() -> list[dict[str, Any]]:
    """Return all registered skills."""
    return list(_skill_registry)


def get_active_skill() -> dict[str, Any] | None:
    """Return the currently active skill, or None."""
    return _active_skill


def set_active_skill(skill: dict[str, Any] | None) -> None:
    """Set (or clear) the active skill."""
    global _active_skill
    _active_skill = skill


async def reload_skills(extra_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    """Reload the skill registry from disk and return the new list."""
    global _skill_registry
    _skill_registry = await discover_skills(extra_dirs)
    return _skill_registry


def find_skill_by_name(name: str) -> dict[str, Any] | None:
    """Find a skill by name (case-insensitive)."""
    lower = name.lower()
    return next((s for s in _skill_registry if s["name"].lower() == lower), None)


# ── System prompt injection ────────────────────────────────────────────────────


def _truncate_body(body: str, max_tokens: int = MAX_SKILL_CONTENT_TOKENS) -> str:
    """Truncate the skill body so it stays within the rough token limit."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n\n[… skill content truncated …]"


def build_skill_system_prompt_section(skill: dict[str, Any]) -> str:
    """
    Build the system prompt section for an active skill.

    Wrapped in ``<active_skill>`` tags so the model can distinguish it
    from the rest of the system prompt.
    """
    body = _truncate_body(skill["body"])
    return "\n".join([
        "<active_skill>",
        f"Name: {skill['name']}",
        f"Description: {skill['description']}",
        "",
        "Instructions:",
        body,
        "</active_skill>",
    ])


# ── UseSkill tool ─────────────────────────────────────────────────────────────


class UseSkillTool:
    """Switch the active skill mid-session."""

    name = "UseSkill"
    description = "Switch to a named skill. Call with empty name to clear the active skill."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Skill name (empty string to clear).",
            }
        },
        "required": ["name"],
    }

    def is_read_only(self) -> bool:
        return False  # changes session state

    def is_enabled(self) -> bool:
        return bool(_skill_registry)  # only available when skills are loaded

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        requested = (input.get("name") or "").strip()

        if not requested:
            set_active_skill(None)
            return {"content": "Active skill cleared."}

        skill = find_skill_by_name(requested)
        if skill is None:
            available = ", ".join(s["name"] for s in _skill_registry) or "(none)"
            return {
                "content": (
                    f"Skill '{requested}' not found. "
                    f"Available skills: {available}"
                ),
                "is_error": True,
            }

        set_active_skill(skill)
        return {"content": f"Switched to skill: {skill['name']}"}


# ── ListSkills tool ────────────────────────────────────────────────────────────


class ListSkillsTool:
    """List all available skills."""

    name = "ListSkills"
    description = "List all available skills by name and description."
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}

    def is_read_only(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if not _skill_registry:
            return {"content": "No skills available."}
        lines = [f"- {s['name']}: {s['description']}" for s in _skill_registry]
        active = get_active_skill()
        if active:
            lines.insert(0, f"Active skill: {active['name']}")
        return {"content": "\n".join(lines)}


# ── Singleton tool instances ───────────────────────────────────────────────────

use_skill_tool = UseSkillTool()
list_skills_tool = ListSkillsTool()
