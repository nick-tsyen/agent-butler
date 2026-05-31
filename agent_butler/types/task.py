from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

TASK_STATUSES: list[str] = ["pending", "in_progress", "completed"]
TaskStatus = Literal["pending", "in_progress", "completed"]


class Task(BaseModel):
    id: str
    subject: str
    description: str
    active_form: str | None = None
    owner: str | None = None
    status: TaskStatus
    blocks: list[str] = []
    blocked_by: list[str] = []
    metadata: dict[str, Any] | None = None
