from __future__ import annotations

import re
from typing import Any

from ...types.skill import SkillFrontmatter


def _as_string(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _as_string_array(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _as_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return False


def split_frontmatter(content: str) -> dict[str, Any]:
    pattern = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$")
    match = pattern.match(content)
    if not match:
        return {"raw": {}, "body": content}

    yaml_text = match.group(1)
    body = match.group(2)

    try:
        import yaml
        parsed = yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            return {"raw": parsed, "body": body}
        return {
            "raw": {},
            "body": body,
            "parseError": "Frontmatter must be a YAML mapping (key: value)",
        }
    except Exception as exc:
        return {"raw": {}, "body": body, "parseError": str(exc)}


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    result = split_frontmatter(content)
    return result["raw"], result["body"]


def extract_fallback_description(body: str) -> str | None:
    lines = body.splitlines()
    buf: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if buf:
                break
            continue
        if not buf and line.startswith("#"):
            continue
        buf.append(line)
    if not buf:
        return None
    desc = " ".join(buf)
    return re.sub(r"\s+", " ", desc).strip() or None


def normalize_frontmatter(
    raw: dict[str, Any],
    body: str,
) -> SkillFrontmatter:
    allowed_tools = _as_string_array(raw.get("allowed-tools", raw.get("allowedTools")))
    paths = _as_string_array(raw.get("paths"))

    return SkillFrontmatter(
        name=_as_string(raw.get("name")),
        description=_as_string(raw.get("description")),
        when_to_use=_as_string(raw.get("when_to_use", raw.get("whenToUse"))),
        allowed_tools=allowed_tools,
        argument_hint=_as_string(raw.get("argument-hint", raw.get("argumentHint"))),
        disable_model_invocation=_as_boolean(
            raw.get("disable-model-invocation", raw.get("disableModelInvocation")),
        ),
        paths=paths if paths else None,
        has_fork_context=_as_string(raw.get("context")) == "fork",
        raw=raw,
    )
