from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, Callable

from ..permissions.permissions import (
    PermissionRuleSet,
    PermissionSettings,
    load_permission_settings,
)
from ..tools.base import Tool
from ..tools.registry import get_all_tools
from .agentic_loop import query


class QueryEngine:
    def __init__(
        self,
        cwd: str = ".",
        model: str | None = None,
        system_prompt: str = "",
        tools: list[Tool] | None = None,
        permission_settings: PermissionSettings | None = None,
        session_rules: PermissionRuleSet | None = None,
        on_permission_request: Callable | None = None,
        max_turns: int = 100,
        session_id: str | None = None,
    ) -> None:
        self.cwd = cwd
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else get_all_tools()
        self.permission_settings = permission_settings or load_permission_settings(cwd)
        self.session_rules = session_rules or PermissionRuleSet()
        self.on_permission_request = on_permission_request
        self.max_turns = max_turns
        self.session_id = session_id

    async def submit(
        self,
        messages: list[dict[str, Any]],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        tools: list[Tool] | None = None,
        max_turns: int | None = None,
        abort_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        effective_prompt = system_prompt if system_prompt is not None else self.system_prompt
        effective_model = model or self.model
        effective_tools = tools or self.tools
        effective_max_turns = max_turns if max_turns is not None else self.max_turns

        async for event in query(
            messages=messages,
            system_prompt=effective_prompt,
            tools=effective_tools,
            model=effective_model,
            cwd=self.cwd,
            max_turns=effective_max_turns,
            permission_settings=self.permission_settings,
            session_rules=self.session_rules,
            on_permission_request=self.on_permission_request,
            abort_event=abort_event,
            default_model=self.model,
            session_id=self.session_id,
        ):
            yield event
