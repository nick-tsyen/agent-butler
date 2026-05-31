from __future__ import annotations

from .memdir import read_project_memories


def _score_text_match(haystack: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in haystack)


def find_relevant_memories(cwd: str, query: str) -> list[dict]:
    memories = read_project_memories(cwd)
    if not memories:
        return []

    terms = query.lower().split()
    scored: list[tuple[int, dict]] = []

    for memory in memories:
        searchable = f"{memory['name']} {memory['description']} {memory['body']}".lower()
        score = _score_text_match(searchable, terms)
        if score > 0:
            scored.append((score, memory))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [memory for _, memory in scored]
