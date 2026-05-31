from __future__ import annotations

from pathlib import Path

from ...types.skill import Skill, SkillSource
from ...utils.paths import get_agent_butler_path, get_project_agent_butler_dir
from .parse_frontmatter import (
    extract_fallback_description,
    normalize_frontmatter,
    split_frontmatter,
)

SKILL_FILE = "SKILL.md"


def get_user_skills_dir() -> str:
    return get_agent_butler_path("skills")


def get_project_skills_dir(cwd: str) -> str:
    return str(Path(get_project_agent_butler_dir(cwd)) / "skills")


async def load_skills_from_dir(dir_path: str, source: SkillSource) -> list[Skill]:
    skills: list[Skill] = []
    dir_obj = Path(dir_path)

    if not dir_obj.is_dir():
        return skills

    try:
        entries = sorted(
            e.name for e in dir_obj.iterdir() if e.is_dir()
        )
    except OSError:
        return skills

    for dir_name in entries:
        skill_dir = dir_obj / dir_name
        file_path = skill_dir / SKILL_FILE

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError:
            continue

        split = split_frontmatter(raw_text)
        if split.get("parseError"):
            continue

        frontmatter = normalize_frontmatter(split["raw"], split["body"])

        try:
            real_file = str(file_path.resolve())
        except OSError:
            real_file = str(file_path)
        try:
            real_dir = str(skill_dir.resolve())
        except OSError:
            real_dir = str(skill_dir)

        name = frontmatter.name or dir_name
        description = (
            frontmatter.description
            or extract_fallback_description(split["body"])
            or name
        )

        skills.append(Skill(
            name=name,
            description=description,
            when_to_use=frontmatter.when_to_use,
            body=split["body"],
            file_path=real_file,
            base_dir=real_dir,
            source=source,
            frontmatter=frontmatter,
        ))

    return skills


async def load_all_skills(cwd: str) -> dict:
    user_dir = get_user_skills_dir()
    project_dir = get_project_skills_dir(cwd)

    import asyncio
    user_skills, project_skills = await asyncio.gather(
        load_skills_from_dir(user_dir, "user"),
        load_skills_from_dir(project_dir, "project"),
    )

    seen_real_paths: set[str] = set()
    by_name: dict[str, Skill] = {}
    warnings: list[str] = []

    for skill in [*user_skills, *project_skills]:
        if skill.file_path in seen_real_paths:
            continue
        seen_real_paths.add(skill.file_path)
        by_name[skill.name] = skill

    return {"skills": list(by_name.values()), "warnings": warnings}
