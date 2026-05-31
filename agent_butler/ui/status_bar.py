from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .spinner import Spinner


class StatusBar:
    def __init__(self) -> None:
        self._model: str = ""
        self._mode: str = "default"
        self._context_percent: int = 0
        self._tokens_in: int = 0
        self._tokens_out: int = 0
        self._is_loading: bool = False
        self._spinner_label: str = "Thinking"
        self._streaming_text: str = ""
        self._permission_prompt: dict | None = None
        self._spinner: Spinner | None = None
        self._notice: dict | None = None

    def set_model(self, model: str) -> None:
        self._model = model

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def set_usage(self, tokens_in: int, tokens_out: int, context_percent: int = 0) -> None:
        self._tokens_in = tokens_in
        self._tokens_out = tokens_out
        self._context_percent = context_percent

    def set_loading(self, loading: bool, label: str = "Thinking") -> None:
        self._is_loading = loading
        self._spinner_label = label
        if loading and not self._spinner:
            self._spinner = Spinner(label)
        elif loading and self._spinner:
            self._spinner.update_label(label)
        elif not loading:
            self._spinner = None

    def set_streaming_text(self, text: str) -> None:
        self._streaming_text = text

    def set_permission_prompt(self, prompt: dict | None) -> None:
        self._permission_prompt = prompt

    def set_notice(self, notice: dict | None) -> None:
        self._notice = notice

    def render(self) -> Group:
        renderables: list = []

        if self._notice:
            tone = self._notice.get("tone", "info")
            title = self._notice.get("title", "")
            body = self._notice.get("body", "")
            style = "red" if tone == "error" else "dim"
            renderables.append(Text.assemble(
                (f"  {title}: ", style),
                (body, style),
            ))

        if self._permission_prompt:
            renderables.append(self._render_permission_prompt())
        elif self._is_loading and not self._streaming_text and self._spinner:
            renderables.append(self._spinner.render())
        elif self._is_loading and self._streaming_text:
            renderables.append(Text.assemble(
                ("▎ ", "magenta"),
                (self._streaming_text, ""),
            ))

        if not self._is_loading and (self._tokens_in or self._tokens_out):
            text = Text()
            text.append("  tokens: ", style="dim")
            total = self._tokens_in + self._tokens_out
            text.append(f"{total:,}", style="dim")
            text.append(f" total ({self._tokens_in:,} in / {self._tokens_out:,} out)", style="dim")
            if self._context_percent:
                text.append(f"  context: {self._context_percent}%", style="dim")
            renderables.append(text)

        if not renderables:
            renderables.append(Text(""))

        return Group(*renderables)

    def _render_permission_prompt(self) -> Panel:
        prompt = self._permission_prompt
        tool_name = prompt.get("tool_name", "")
        summary = prompt.get("summary", "")
        risk = prompt.get("risk", "")
        rule_hint = prompt.get("rule_hint", "")

        text = Text()
        text.append(f"⚠ Permission required: {tool_name}\n", style="yellow")
        text.append(f"  args: {summary}\n", style="dim")
        text.append(f"  risk: {risk}\n", style="dim")
        text.append(f"  always allow rule: {rule_hint}\n", style="dim")
        text.append("  [y] allow once   [n] deny   [a] always allow (session)", style="cyan")

        return Panel(text, border_style="yellow", expand=True)
