from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..types.tool import ToolContext, ToolResult

DEFAULT_MAX_RESULT_SIZE_CHARS = 100_000


def truncate_tool_result(content: str, max_chars: int | None = None) -> str:
    limit = max_chars or DEFAULT_MAX_RESULT_SIZE_CHARS
    if len(content) <= limit:
        return content
    truncated = content[:limit]
    return f"{truncated}\n\n[Output truncated: {len(content)} chars total, showing first {limit}]"


def tool_to_api_param(tool: Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]: ...

    @property
    def max_result_size_chars(self) -> int | None:
        return None

    @abstractmethod
    async def call(self, input_data: dict[str, Any], context: ToolContext) -> ToolResult: ...

    @abstractmethod
    def is_read_only(self) -> bool: ...

    @abstractmethod
    def is_enabled(self) -> bool: ...

    def is_concurrency_safe(self, input_data: dict[str, Any] | None = None) -> bool:
        return False
