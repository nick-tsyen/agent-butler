from __future__ import annotations

import sys

from .load_skills_dir import load_all_skills
from .registry import set_skills


class SkillsBootstrapResult:
    def __init__(
        self,
        skill_count: int,
        conditional_count: int,
        warnings: list[str],
    ) -> None:
        self.skill_count = skill_count
        self.conditional_count = conditional_count
        self.warnings = warnings


async def bootstrap_skills(cwd: str | None = None) -> SkillsBootstrapResult:
    if cwd is None:
        import os
        cwd = os.getcwd()

    result = await load_all_skills(cwd)
    skills = result["skills"]
    warnings = result["warnings"]

    set_skills(skills)

    conditional_count = sum(
        1 for s in skills
        if s.frontmatter.paths and len(s.frontmatter.paths) > 0
    )

    for warning in warnings:
        print(f"[agent-butler] {warning}", file=sys.stderr)

    return SkillsBootstrapResult(
        skill_count=len(skills) - conditional_count,
        conditional_count=conditional_count,
        warnings=warnings,
    )
