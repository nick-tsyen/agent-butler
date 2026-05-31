from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.text import Text


class TodoListView:
    def __init__(self) -> None:
        self._todos: list[dict[str, Any]] = []

    def set_todos(self, todos: list[dict[str, Any]]) -> None:
        self._todos = list(todos)

    def render(self) -> Group:
        if not self._todos:
            return Group(Text(""))

        renderables: list[Text] = []
        for todo in self._todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            active_form = todo.get("activeForm", "")

            if status == "completed":
                prefix = "[x]"
                style = "dim"
            elif status == "in_progress":
                prefix = "[~]"
                style = "yellow"
            else:
                prefix = "[ ]"
                style = ""

            text = Text()
            text.append(f"  {prefix} ", style=style)
            text.append(content, style=style)
            if status == "in_progress" and active_form:
                text.append(f" ({active_form})", style="dim")
            renderables.append(text)

        return Group(*renderables)
