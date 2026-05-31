from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

TodoStatus = Literal["pending", "in_progress", "completed"]


class TodoItem(BaseModel):
    content: str
    status: TodoStatus
    active_form: str
