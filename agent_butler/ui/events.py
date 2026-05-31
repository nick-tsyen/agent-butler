from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass
class UITextDelta:
    text: str


@dataclass
class UIToolStart:
    id: str
    name: str
    input_preview: str = ""


@dataclass
class UIToolDone:
    id: str
    name: str
    result_length: int = 0
    is_error: bool = False
    error_message: str | None = None
    display_name: str | None = None
    display_hint: str | None = None


@dataclass
class UIPermissionRequest:
    tool_name: str
    summary: str
    risk: str
    rule_hint: str
    is_plan_exit: bool = False
    plan_content: str | None = None


@dataclass
class UIAssistantMessage:
    content: Any = None


@dataclass
class UIToolResultMessage:
    pass


@dataclass
class UIUsageUpdate:
    turn_input: int = 0
    turn_output: int = 0
    total_input: int = 0
    total_output: int = 0
    context_percent: int = 0


@dataclass
class UISystemNotice:
    tone: str = "info"
    title: str = ""
    body: str = ""


@dataclass
class UIError:
    message: str = ""


@dataclass
class UITurnComplete:
    reason: str = "end_turn"
    turn_count: int = 0


UIEvent = Union[
    UITextDelta,
    UIToolStart,
    UIToolDone,
    UIPermissionRequest,
    UIAssistantMessage,
    UIToolResultMessage,
    UIUsageUpdate,
    UISystemNotice,
    UIError,
    UITurnComplete,
]
