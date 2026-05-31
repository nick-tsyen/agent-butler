from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ...utils.paths import get_projects_root
from .memory_types import is_memory_type

MEMORY_ENTRYPOINT = "MEMORY.md"
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000


def _sanitize_slug(input_str: str) -> str:
    slug = input_str.lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] if slug else "project"


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _find_canonical_git_root(cwd: str) -> str:
    current = Path(cwd).resolve()
    while True:
        if (current / ".git").exists():
            return str(current)
        parent = current.parent
        if parent == current:
            return str(Path(cwd).resolve())
        current = parent


def _get_project_path_info(cwd: str) -> dict[str, str]:
    git_root = _find_canonical_git_root(cwd)
    slug_base = _sanitize_slug(Path(git_root).name)
    suffix = hashlib.sha256(git_root.encode()).hexdigest()[:16]
    project_key = f"{slug_base}-{suffix}"
    return {
        "git_root": git_root,
        "project_key": project_key,
        "project_dir": str(Path(get_projects_root()) / project_key),
    }


def _get_project_memory_dir(cwd: str) -> str:
    info = _get_project_path_info(cwd)
    return str(Path(info["project_dir"]) / "memory")


def ensure_memory_dir_exists(cwd: str) -> str:
    memory_dir = Path(_get_project_memory_dir(cwd))
    memory_dir.mkdir(parents=True, exist_ok=True)
    entrypoint = memory_dir / MEMORY_ENTRYPOINT
    if not entrypoint.exists():
        entrypoint.write_text("# Project Memory\n\n", encoding="utf-8")
    return str(memory_dir)


def _parse_frontmatter(raw: str) -> dict[str, str] | None:
    match = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    if not match:
        return None

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        idx = line.find(":")
        if idx == -1:
            continue
        fields[line[:idx].strip()] = line[idx + 1:].strip()

    name = fields.get("name")
    description = fields.get("description")
    type_val = fields.get("type")
    if not name or not description or not type_val or not is_memory_type(type_val):
        return None

    return {
        "name": _normalize_line(name),
        "description": _normalize_line(description),
        "type": type_val,
    }


def _strip_frontmatter(raw: str) -> str:
    return re.sub(r"^---\n[\s\S]*?\n---\n?", "", raw).strip()


def _truncate_entrypoint(raw: str) -> tuple[str, str | None]:
    content = raw
    line_truncated = False
    byte_truncated = False

    lines = content.splitlines()
    if len(lines) > MAX_ENTRYPOINT_LINES:
        content = "\n".join(lines[:MAX_ENTRYPOINT_LINES])
        line_truncated = True

    while len(content.encode("utf-8")) > MAX_ENTRYPOINT_BYTES and content:
        content = content[:-1]
        byte_truncated = True

    warning = None
    if line_truncated or byte_truncated:
        parts = []
        if line_truncated:
            parts.append("by line limit")
        if byte_truncated:
            parts.append("by byte limit")
        warning = f"> WARNING: MEMORY.md was truncated {' and '.join(parts)}."

    return content.strip(), warning


def _build_pointer_line(entry: dict[str, str]) -> str:
    return f"- [{_normalize_line(entry['title'])}]({entry['fileName']}) — {_normalize_line(entry['hook'])}"


def _slugify_memory_file_name(name: str) -> str:
    return _sanitize_slug(name).replace(".", "-") + ".md"


def _collect_memory_markdown_files(memory_dir: str, current_dir: str | None = None) -> list[str]:
    if current_dir is None:
        current_dir = memory_dir
    results: list[str] = []
    current_path = Path(current_dir)

    for entry in current_path.iterdir():
        full_path = current_path / entry.name
        if entry.is_dir():
            results.extend(_collect_memory_markdown_files(memory_dir, str(full_path)))
        elif entry.is_file() and entry.name.endswith(".md") and entry.name != MEMORY_ENTRYPOINT:
            results.append(str(full_path.relative_to(memory_dir)))

    return results


def _list_memory_files(cwd: str) -> list[dict]:
    memory_dir = ensure_memory_dir_exists(cwd)
    relative_paths = _collect_memory_markdown_files(memory_dir)
    docs = []

    for rel_path in relative_paths:
        file_path = Path(memory_dir) / rel_path
        raw = file_path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(raw)
        if not frontmatter:
            continue
        docs.append({
            "fileName": rel_path,
            "relativePath": rel_path,
            "filePath": str(file_path),
            "title": frontmatter["name"],
            "hook": frontmatter["description"],
            "frontmatter": frontmatter,
            "body": _strip_frontmatter(raw),
        })

    return docs


def _find_existing_memory_file(cwd: str, name: str, description: str) -> str | None:
    docs = _list_memory_files(cwd)
    normalized_name = _normalize_line(name).lower()
    normalized_desc = _normalize_line(description).lower()

    for doc in docs:
        if doc["frontmatter"]["name"].lower() == normalized_name:
            return doc["fileName"]

    for doc in docs:
        existing = f"{doc['frontmatter']['name']} {doc['frontmatter']['description']}".lower()
        if normalized_name in existing or normalized_desc in existing:
            return doc["fileName"]

    return None


def _rewrite_entrypoint(memory_dir: str, entries: list[dict[str, str]]) -> None:
    entrypoint_path = Path(memory_dir) / MEMORY_ENTRYPOINT
    unique: dict[str, str] = {}
    for entry in entries:
        unique[entry["fileName"]] = _build_pointer_line(entry)

    body_lines = ["# Project Memory", "", *unique.values()]
    content, warning = _truncate_entrypoint("\n".join(body_lines))
    parts = [content]
    if warning:
        parts.append(warning)
    final_text = "\n\n".join(parts) + "\n"
    entrypoint_path.write_text(final_text, encoding="utf-8")


def write_project_memory(
    cwd: str,
    name: str,
    description: str,
    type: str,
    content: str,
    file_name: str | None = None,
) -> dict[str, str | bool]:
    if not is_memory_type(type):
        raise ValueError(f"Invalid memory type: {type}. Must be one of: user, feedback, project, reference")

    memory_dir = ensure_memory_dir_exists(cwd)
    existing_file_name = file_name or _find_existing_memory_file(cwd, name, description)
    file_name_final = existing_file_name or _slugify_memory_file_name(name)
    file_path = Path(memory_dir) / file_name_final

    body = "\n".join([
        "---",
        f"name: {_normalize_line(name)}",
        f"description: {_normalize_line(description)}",
        f"type: {type}",
        "---",
        "",
        content.strip(),
        "",
    ])

    file_path.write_text(body, encoding="utf-8")

    docs = _list_memory_files(cwd)
    _rewrite_entrypoint(memory_dir, [
        {
            "fileName": doc["fileName"],
            "filePath": doc["filePath"],
            "title": doc["frontmatter"]["name"],
            "hook": doc["frontmatter"]["description"],
        }
        for doc in docs
    ])

    return {
        "filePath": str(file_path),
        "fileName": file_name_final,
        "updatedExisting": existing_file_name is not None,
    }


def read_project_memories(cwd: str) -> list[dict]:
    docs = _list_memory_files(cwd)
    return [
        {
            "fileName": doc["fileName"],
            "filePath": doc["filePath"],
            "name": doc["frontmatter"]["name"],
            "description": doc["frontmatter"]["description"],
            "type": doc["frontmatter"]["type"],
            "body": doc["body"],
        }
        for doc in docs
    ]
