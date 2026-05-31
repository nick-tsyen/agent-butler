from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    cwd: str
    abort_event: Any | None = None
    set_permission_mode: Any | None = None
    get_permission_mode: Any | None = None
    add_session_allow_rules: Any | None = None
    session_id: str | None = None
    permission_settings: Any | None = None
    session_permission_rules: Any | None = None
    on_permission_request: Any | None = None
    default_model: str | None = None
    tool_use_id: str | None = None


class ToolResult(BaseModel):
    content: str
    is_error: bool | None = None
