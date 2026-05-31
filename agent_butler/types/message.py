from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, list[ContentBlock]]
    is_error: bool | None = None


class ThinkingBlock(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str | None = None


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock, ThinkingBlock]


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: Union[str, list[ContentBlock]]


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Union[str, list[ContentBlock]]


Message = Union[UserMessage, AssistantMessage]


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None


class StreamTextEvent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class StreamToolUseStartEvent(BaseModel):
    type: Literal["tool_use_start"] = "tool_use_start"
    id: str
    name: str


class StreamToolUseInputEvent(BaseModel):
    type: Literal["tool_use_input"] = "tool_use_input"
    id: str
    partial_json: str


class StreamMessageStartEvent(BaseModel):
    type: Literal["message_start"] = "message_start"
    message_id: str


class StreamMessageDoneEvent(BaseModel):
    type: Literal["message_done"] = "message_done"
    stop_reason: str
    usage: Usage


class StreamErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    error: str


StreamEvent = Union[
    StreamTextEvent,
    StreamToolUseStartEvent,
    StreamToolUseInputEvent,
    StreamMessageStartEvent,
    StreamMessageDoneEvent,
    StreamErrorEvent,
]
