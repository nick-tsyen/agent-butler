from __future__ import annotations

import os

from ...types.skill import Skill

MAX_LISTING_DESC_CHARS = 250
MIN_DESC_CHARS_PER_SKILL = 20
DEFAULT_BUDGET_CHARS = 8000


def get_skill_char_budget() -> int:
    env_value = os.environ.get("AGENT_BUTLER_SKILL_CHAR_BUDGET", "")
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_BUDGET_CHARS


def _truncate_desc(desc: str, max_len: int) -> str:
    if len(desc) <= max_len:
        return desc
    if max_len <= 1:
        return "…"
    return desc[: max_len - 1].rstrip() + "…"


def _build_line(skill: Skill, desc_max: int) -> str:
    capped = min(desc_max, MAX_LISTING_DESC_CHARS)
    full_desc = skill.description
    if skill.when_to_use:
        full_desc = f"{skill.description} — {skill.when_to_use}"
    desc = _truncate_desc(full_desc, capped)
    return f"- {skill.name}: {desc}"


def _build_name_only(skill: Skill) -> str:
    return f"- {skill.name}"


def format_skills_within_budget(
    skills: list[Skill],
    budget: int | None = None,
) -> str:
    if not skills:
        return ""

    if budget is None:
        budget = get_skill_char_budget()

    tier1 = [_build_line(s, MAX_LISTING_DESC_CHARS) for s in skills]
    tier1_total = sum(len(line) + 1 for line in tier1)
    if tier1_total <= budget:
        return "\n".join(tier1)

    prefix_cost = sum(len(f"- {s.name}: ") + 1 for s in skills)
    desc_budget = budget - prefix_cost
    if desc_budget >= len(skills) * MIN_DESC_CHARS_PER_SKILL:
        per_desc = max(MIN_DESC_CHARS_PER_SKILL, desc_budget // len(skills))
        tier2 = [_build_line(s, per_desc) for s in skills]
        tier2_total = sum(len(line) + 1 for line in tier2)
        if tier2_total <= budget:
            return "\n".join(tier2)

    return "\n".join(_build_name_only(s) for s in skills)


def format_skills_system_reminder(skills: list[Skill]) -> str:
    if not skills:
        return ""
    listing = format_skills_within_budget(skills)
    if not listing:
        return ""
    return "\n".join([
        "<system-reminder>",
        'Available skills you can invoke via the `Skill` tool. Each line is `- <name>: <description>`.',
        'Call `Skill(skill="<name>", args="<optional args>")` when the user\'s request matches one of these.',
        "",
        listing,
        "</system-reminder>",
    ])
