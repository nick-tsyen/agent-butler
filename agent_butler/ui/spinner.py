from __future__ import annotations

import time

from rich.text import Text

STAR_CHARS = ["·", "✢", "✳", "✶", "✻", "✽"]
SPINNER_FRAMES = STAR_CHARS + STAR_CHARS[-2:0:-1]

STAR_FRAME_MS = 120
SHIMMER_STEP_MS = 80
SHIMMER_HALF_WIDTH = 1
REST_PADDING = 10

COLOR_BASE = "#D77757"
COLOR_SHIMMER = "#F59575"


class Spinner:
    def __init__(self, label: str = "Thinking") -> None:
        self._label = label
        self._start_time = time.monotonic()

    def update_label(self, label: str) -> None:
        self._label = label

    def render(self) -> Text:
        elapsed_ms = (time.monotonic() - self._start_time) * 1000
        star_idx = int(elapsed_ms / STAR_FRAME_MS) % len(SPINNER_FRAMES)
        star = SPINNER_FRAMES[star_idx]

        message = f"{self._label}\u2026"
        before, shimmer, after = _slice_shimmer(message, elapsed_ms)

        text = Text()
        text.append(f"{star} ", style=COLOR_BASE)
        if before:
            text.append(before, style=COLOR_BASE)
        if shimmer:
            text.append(shimmer, style=COLOR_SHIMMER)
        if after:
            text.append(after, style=COLOR_BASE)
        return text


def _slice_shimmer(text: str, time_ms: float) -> tuple[str, str, str]:
    length = len(text)
    if length == 0:
        return ("", "", "")

    tick = int(time_ms / SHIMMER_STEP_MS)
    cycle_length = length + REST_PADDING * 2
    glimmer_index = length + REST_PADDING - (tick % cycle_length)
    start = glimmer_index - SHIMMER_HALF_WIDTH
    end_excl = glimmer_index + SHIMMER_HALF_WIDTH + 1

    if start >= length or end_excl <= 0:
        return (text, "", "")

    s = max(0, start)
    e = min(length, end_excl)
    return (text[:s], text[s:e], text[e:])
