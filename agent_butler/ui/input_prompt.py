from __future__ import annotations

import asyncio
from typing import Any


class InputPrompt:
    def __init__(self) -> None:
        self._session: Any = None
        self._history: list[str] = []

    async def get_input(self, prompt_text: str = "> ") -> str:
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import InMemoryHistory

            if self._session is None:
                self._session = PromptSession(history=InMemoryHistory())

            result = await self._session.prompt_async(prompt_text)
            if result.strip():
                self._history.append(result.strip())
            return result
        except ImportError:
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, lambda: input(prompt_text))
            return line
        except (EOFError, KeyboardInterrupt):
            return ""
