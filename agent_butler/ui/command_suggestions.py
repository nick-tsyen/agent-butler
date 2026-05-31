from __future__ import annotations

from rich.console import Group
from rich.text import Text

COMMANDS = [
    ("/help", "Show available commands"),
    ("/clear", "Clear conversation history"),
    ("/cost", "Show session token usage"),
    ("/model", "Inspect or override the session model"),
    ("/mode", "Inspect or switch permission mode"),
    ("/tasks", "Switch task system or reset the task graph"),
    ("/compact", "Compact conversation context"),
    ("/mcp", "Inspect MCP servers and their tools"),
    ("/skills", "List loaded skills"),
    ("/agents", "List built-in + custom sub-agent definitions"),
    ("/resume", "Resume a previous session"),
    ("/exit", "Exit session"),
]


class CommandSuggestions:
    def __init__(self) -> None:
        self._query: str = ""
        self._selected: int = 0

    def set_query(self, query: str) -> None:
        self._query = query
        self._selected = 0

    def get_matches(self) -> list[tuple[str, str]]:
        if not self._query:
            return []
        q = self._query.lower()
        return [(name, desc) for name, desc in COMMANDS if name.startswith(q)]

    def render(self) -> Group:
        matches = self.get_matches()
        if not matches:
            return Group(Text(""))

        renderables: list[Text] = []
        for i, (name, desc) in enumerate(matches[:6]):
            if i == self._selected:
                renderables.append(Text.assemble(
                    (f"  ❯ {name}", "cyan bold"),
                    (f"  {desc}", "dim"),
                ))
            else:
                renderables.append(Text.assemble(
                    (f"    {name}", "cyan"),
                    (f"  {desc}", "dim"),
                ))
        return Group(*renderables)
