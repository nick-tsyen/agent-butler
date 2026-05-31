from __future__ import annotations

from agent_butler.types.message import (
    AssistantMessage,
    StreamMessageDoneEvent,
    StreamMessageStartEvent,
    StreamTextEvent,
    Usage,
)


class TestStreamEvents:
    def test_stream_text_event(self) -> None:
        event = StreamTextEvent(text="hello")
        assert event.type == "text"
        assert event.text == "hello"

    def test_stream_message_start_event(self) -> None:
        event = StreamMessageStartEvent(message_id="msg-123")
        assert event.type == "message_start"
        assert event.message_id == "msg-123"

    def test_stream_message_done_event(self) -> None:
        usage = Usage(input_tokens=100, output_tokens=50)
        event = StreamMessageDoneEvent(stop_reason="end_turn", usage=usage)
        assert event.type == "message_done"
        assert event.stop_reason == "end_turn"
        assert event.usage.input_tokens == 100
        assert event.usage.output_tokens == 50


class TestUsage:
    def test_usage_defaults(self) -> None:
        usage = Usage(input_tokens=0, output_tokens=0)
        assert usage.cache_creation_input_tokens is None
        assert usage.cache_read_input_tokens is None

    def test_usage_with_cache(self) -> None:
        usage = Usage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=25,
            cache_read_input_tokens=10,
        )
        assert usage.cache_creation_input_tokens == 25
        assert usage.cache_read_input_tokens == 10


class TestAssistantMessage:
    def test_string_content(self) -> None:
        msg = AssistantMessage(content="Hello world")
        assert msg.role == "assistant"
        assert msg.content == "Hello world"

    def test_list_content(self) -> None:
        from agent_butler.types.message import TextBlock
        blocks = [TextBlock(text="Hello"), TextBlock(text="World")]
        msg = AssistantMessage(content=blocks)
        assert msg.role == "assistant"
        assert len(msg.content) == 2
