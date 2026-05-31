from __future__ import annotations

from ...types.skill import Skill

_dynamic: dict[str, Skill] = {}
_conditional: dict[str, Skill] = {}
_initialized = False


def set_skills(skills: list[Skill]) -> None:
    global _initialized
    _dynamic.clear()
    _conditional.clear()
    for skill in skills:
        if skill.frontmatter.paths and len(skill.frontmatter.paths) > 0:
            _conditional[skill.name] = skill
        else:
            _dynamic[skill.name] = skill
    _initialized = True


def is_skills_initialized() -> bool:
    return _initialized


def get_model_visible_skills() -> list[Skill]:
    return [s for s in _dynamic.values() if not s.frontmatter.disable_model_invocation]


def get_all_user_invocable_skills() -> list[Skill]:
    return [*_dynamic.values(), *_conditional.values()]


def register_skill(skill: Skill) -> None:
    if skill.frontmatter.paths and len(skill.frontmatter.paths) > 0:
        _conditional[skill.name] = skill
    else:
        _dynamic[skill.name] = skill


def find_skill(name: str) -> Skill | None:
    return _dynamic.get(name) or _conditional.get(name)


def get_all_skills() -> list[Skill]:
    return [*_dynamic.values(), *_conditional.values()]


def activate_conditional(name: str) -> bool:
    skill = _conditional.pop(name, None)
    if not skill:
        return False
    _dynamic[name] = skill
    return True


def list_conditional_skills() -> list[Skill]:
    return list(_conditional.values())


def clear_skills() -> None:
    global _initialized
    _dynamic.clear()
    _conditional.clear()
    _initialized = False
