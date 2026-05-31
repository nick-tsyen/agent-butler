"""
Step 10 - Project memory with file-based long-term knowledge

Goal:
- store long-term project memory as markdown files
- keep one lightweight MEMORY.md index as the entrypoint
- separate memory from transcript history
- make memory human-readable, editable, and easy to inject into prompts

This file is intentionally smaller than the production memory system.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import aiofiles

# ── Constants ─────────────────────────────────────────────────────────────────

AGENT_BUTLER_HOME: Path = Path.home() / ".agent-butler"
PROJECTS_DIR: Path = AGENT_BUTLER_HOME / "projects"
MEMORY_DIR_NAME: str = "memory"
MEMORY_ENTRYPOINT: str = "MEMORY.md"
MAX_ENTRYPOINT_LINES: int = 200
MAX_ENTRYPOINT_BYTES: int = 25_000

# Valid memory types; anything else is rejected.
MEMORY_TYPES: frozenset[str] = frozenset(["user", "feedback", "project", "reference"])


# ── Project paths ─────────────────────────────────────────────────────────────


def get_project_key(cwd: str) -> str:
    """SHA-256 hash of the absolute project path, truncated to 16 hex chars."""
    return hashlib.sha256(os.path.abspath(cwd).encode()).hexdigest()[:16]


def get_project_memory_paths(cwd: str) -> dict[str, Path]:
    """Return all relevant memory filesystem paths for a project."""
    project_key = get_project_key(cwd)
    project_dir = PROJECTS_DIR / project_key
    memory_dir = project_dir / MEMORY_DIR_NAME
    entrypoint_path = memory_dir / MEMORY_ENTRYPOINT
    return {
        "project_key": project_key,  # type: ignore[dict-item]
        "project_dir": project_dir,
        "memory_dir": memory_dir,
        "entrypoint_path": entrypoint_path,
    }


async def ensure_memory_dir(cwd: str) -> dict[str, Path]:
    """Create the memory directory if it doesn't exist and return paths."""
    paths = get_project_memory_paths(cwd)
    paths["memory_dir"].mkdir(parents=True, exist_ok=True)
    return paths


# ── Slug / HTML helpers ───────────────────────────────────────────────────────


def slugify(value: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower().strip())
    slug = slug.strip("_")
    return slug or "memory_note"


def strip_html_comments(content: str) -> str:
    """Remove <!-- ... --> HTML comments from *content*."""
    return re.sub(r"<!--[\s\S]*?-->", "", content).strip()


# ── Validation ─────────────────────────────────────────────────────────────────


def should_store_as_memory(candidate: dict[str, Any] | None) -> bool:
    """
    Return True when *candidate* is a valid memory payload.

    A valid memory must have a known type, non-empty name / description /
    body, and a description no longer than 200 characters.
    """
    if not candidate:
        return False
    if candidate.get("type") not in MEMORY_TYPES:
        return False
    if not candidate.get("name") or not candidate.get("description") or not candidate.get("body"):
        return False
    if len(candidate["description"]) > 200:
        return False
    return True


# ── File content builders ─────────────────────────────────────────────────────


def build_memory_file_content(
    *, name: str, description: str, type: str, body: str
) -> str:
    """Render a memory dict as a markdown file with YAML frontmatter."""
    return "\n".join([
        "---",
        f"name: {name}",
        f"description: {description}",
        f"type: {type}",
        "---",
        "",
        body.strip(),
        "",
    ])


def parse_frontmatter(raw: str) -> dict[str, str] | None:
    """
    Parse a memory markdown file's YAML frontmatter.

    Returns None if the frontmatter is missing or incomplete.
    """
    match = re.match(r"^---\n([\s\S]*?)\n---\n?([\s\S]*)$", raw)
    if not match:
        return None

    header, body = match.group(1), match.group(2).strip()
    fields: dict[str, str] = {}
    for line in header.splitlines():
        idx = line.find(":")
        if idx == -1:
            continue
        key = line[:idx].strip()
        value = line[idx + 1:].strip()
        fields[key] = value

    if not fields.get("name") or not fields.get("description") or not fields.get("type"):
        return None

    return {
        "name": fields["name"],
        "description": fields["description"],
        "type": fields["type"],
        "body": body,
    }


# ── File I/O ──────────────────────────────────────────────────────────────────


async def write_memory_file(cwd: str, memory: dict[str, Any]) -> Path:
    """Write a memory payload to disk and return the file path."""
    if not should_store_as_memory(memory):
        raise ValueError("Invalid memory payload.")

    paths = await ensure_memory_dir(cwd)
    file_name = slugify(memory["name"]) + ".md"
    file_path = paths["memory_dir"] / file_name
    content = build_memory_file_content(
        name=memory["name"],
        description=memory["description"],
        type=memory["type"],
        body=memory["body"],
    )
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(content)
    return file_path


async def read_memory_file(file_path: Path) -> dict[str, Any] | None:
    """Read and parse a memory markdown file. Returns None if invalid."""
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        raw = await f.read()
    cleaned = strip_html_comments(raw)
    parsed = parse_frontmatter(cleaned)
    if not parsed:
        return None
    return {"file_path": str(file_path), **parsed}


async def list_memory_files(cwd: str) -> list[Path]:
    """Return all memory file paths for the project (excluding the index)."""
    paths = await ensure_memory_dir(cwd)
    memory_dir = paths["memory_dir"]
    return [
        memory_dir / e.name
        for e in memory_dir.iterdir()
        if e.is_file() and e.suffix == ".md" and e.name != MEMORY_ENTRYPOINT
    ]


# ── Index builder ─────────────────────────────────────────────────────────────


def build_memory_index(memories: list[dict[str, Any]]) -> str:
    """Build a MEMORY.md index from a list of parsed memory dicts."""
    lines = ["# Project Memory", ""]
    for mem in memories:
        file_name = Path(mem["file_path"]).name
        lines.append(f"- [{mem['name']}]({file_name}) — {mem['description']}")

    text = "\n".join(lines).strip() + "\n"

    # Apply line and byte limits.
    limited_lines = text.splitlines()[:MAX_ENTRYPOINT_LINES]
    limited_text = "\n".join(limited_lines)
    if len(limited_text.encode("utf-8")) > MAX_ENTRYPOINT_BYTES:
        limited_text = limited_text.encode("utf-8")[:MAX_ENTRYPOINT_BYTES].decode("utf-8", errors="ignore")

    return limited_text.rstrip() + "\n"


async def rebuild_memory_index(cwd: str) -> str:
    """Rewrite the MEMORY.md index from all current memory files."""
    paths = await ensure_memory_dir(cwd)
    files = await list_memory_files(cwd)

    # Load all memory files concurrently.
    import asyncio
    loaded = await asyncio.gather(*[read_memory_file(f) for f in files])
    memories = [m for m in loaded if m is not None]

    index = build_memory_index(memories)
    async with aiofiles.open(paths["entrypoint_path"], "w", encoding="utf-8") as f:
        await f.write(index)
    return index


async def save_memory(cwd: str, memory: dict[str, Any]) -> Path:
    """Write a memory file then rebuild the index. Returns the new file path."""
    file_path = await write_memory_file(cwd, memory)
    await rebuild_memory_index(cwd)
    return file_path


async def read_memory_entrypoint(cwd: str) -> str | None:
    """Read the MEMORY.md index file. Returns None if it doesn't exist yet."""
    paths = await ensure_memory_dir(cwd)
    try:
        async with aiofiles.open(paths["entrypoint_path"], encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError:
        return None


# ── Relevance search ──────────────────────────────────────────────────────────


async def find_relevant_memories(cwd: str, query: str) -> list[str]:
    """
    Return the top-3 memory files most relevant to *query*.

    Relevance is measured by counting how many query terms appear in the
    combined name + description + body text.  This is a cheap heuristic
    that requires no vector database.
    """
    import asyncio

    files = await list_memory_files(cwd)
    loaded = await asyncio.gather(*[read_memory_file(f) for f in files])
    memories = [m for m in loaded if m is not None]

    # Split query into tokens, ignoring punctuation.
    query_terms = [t for t in re.split(r"\W+", query.lower()) if t]

    scored = []
    for mem in memories:
        haystack = "\n".join([mem["name"], mem["description"], mem["body"]]).lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            scored.append((score, mem))

    # Sort by score descending, return top 3 as formatted strings.
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        "\n\n".join([
            f"# {mem['name']}",
            f"Type: {mem['type']}",
            f"Description: {mem['description']}",
            mem["body"],
        ])
        for _, mem in scored[:3]
    ]
