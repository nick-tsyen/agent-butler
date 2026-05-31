from __future__ import annotations

from dataclasses import dataclass

from rich.console import Group
from rich.text import Text


@dataclass
class ToolCallCard:
    id: str
    name: str
    input_preview: str = ""
    result_length: int = 0
    is_error: bool = False
    error_message: str | None = None
    display_name: str | None = None
    display_hint: str | None = None
    is_complete: bool = False


class ToolCallList:
    def __init__(self) -> None:
        self._cards: list[ToolCallCard] = []

    def add_start(self, id: str, name: str, input_preview: str = "") -> None:
        self._cards.append(ToolCallCard(id=id, name=name, input_preview=input_preview))

    def mark_complete(
        self,
        id: str,
        result_length: int = 0,
        is_error: bool = False,
        error_message: str | None = None,
        display_name: str | None = None,
        display_hint: str | None = None,
    ) -> None:
        for card in self._cards:
            if card.id == id:
                card.is_complete = True
                card.result_length = result_length
                card.is_error = is_error
                card.error_message = error_message
                card.display_name = display_name
                card.display_hint = display_hint
                break

    def clear(self) -> None:
        self._cards.clear()

    def render(self) -> Group:
        renderables: list[Text] = []
        for card in self._cards:
            renderables.append(self._render_card(card))
        return Group(*renderables) if renderables else Group(Text(""))

    def _render_card(self, card: ToolCallCard) -> Text:
        label = card.display_name or card.name
        if not card.is_complete:
            return Text.assemble(("  ⚡ Using tool: ", "yellow"), (label, "yellow"))

        if card.is_error:
            text = Text()
            text.append(f"  ✗ {label}", style="red")
            if card.input_preview:
                text.append(f"  ({card.input_preview})", style="dim")
            text.append(" — error", style="red")
            return text

        text = Text()
        text.append(f"  ✓ {label}", style="green")
        if card.display_hint:
            text.append(f"  {card.display_hint}", style="dim")
        elif card.input_preview:
            text.append(f"  ({card.input_preview})", style="dim")
        else:
            text.append(f" ({card.result_length} chars)", style="dim")
        return text

    def has_pending(self) -> bool:
        return any(not c.is_complete for c in self._cards)
