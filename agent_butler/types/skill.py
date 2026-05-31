from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

SkillSource = Literal["user", "project"]


class SkillFrontmatter(BaseModel):
    name: str | None = None
    description: str | None = None
    when_to_use: str | None = None
    allowed_tools: list[str] = []
    argument_hint: str | None = None
    disable_model_invocation: bool = False
    paths: list[str] | None = None
    has_fork_context: bool = False
    raw: dict[str, Any] = {}


class Skill(BaseModel):
    name: str
    description: str
    when_to_use: str | None = None
    body: str
    file_path: str
    base_dir: str
    source: SkillSource
    frontmatter: SkillFrontmatter
