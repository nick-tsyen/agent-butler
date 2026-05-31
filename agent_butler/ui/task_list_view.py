from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.text import Text


class TaskListView:
    def __init__(self) -> None:
        self._tasks: list[dict[str, Any]] = []

    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self._tasks = list(tasks)

    def render(self) -> Group:
        if not self._tasks:
            return Group(Text(""))

        renderables: list[Text] = []
        for task in self._tasks:
            task_id = task.get("id", "?")
            subject = task.get("subject", "")
            status = task.get("status", "pending")
            blocked_by = task.get("blocked_by", [])

            status_colors = {
                "pending": "dim",
                "in_progress": "yellow",
                "completed": "green",
                "failed": "red",
            }
            color = status_colors.get(status, "")

            text = Text()
            text.append(f"  #{task_id} ", style="cyan")
            text.append(f"[{status}] ", style=color)
            text.append(subject, style=color)
            if blocked_by:
                blockers = ", ".join(str(b) for b in blocked_by)
                text.append(f" [blocked by #{blockers}]", style="dim")
            renderables.append(text)

        return Group(*renderables)
