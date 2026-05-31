from __future__ import annotations

import json
import os
from typing import Any

from ..types.message import Usage

MODEL_CONTEXT_WINDOW_DEFAULT = 200_000
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000
AUTOCOMPACT_BUFFER_TOKENS = 13_000
WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
MANUAL_COMPACT_BUFFER_TOKENS = 3_000

TEXT_CHARS_PER_TOKEN = 4
JSON_CHARS_PER_TOKEN = 2
MESSAGE_OVERHEAD_TOKENS = 12
TOOL_BLOCK_OVERHEAD_TOKENS = 24
FIXED_BINARY_BLOCK_TOKENS = 2_000

MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-haiku-3-20250307": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
    "claude-3-opus-20240229": 200_000,
}


def get_context_window_for_model(model: str) -> int:
    env_override = os.environ.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS")
    if env_override:
        try:
            parsed = int(env_override)
            if parsed > 0:
                return parsed
        except ValueError:
            pass

    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]

    for key, value in MODEL_CONTEXT_WINDOWS.items():
        if model in key or key in model:
            return value

    return MODEL_CONTEXT_WINDOW_DEFAULT


def get_effective_context_window_size(model: str) -> int:
    context_window = get_context_window_for_model(model)
    reserved = min(MAX_OUTPUT_TOKENS_FOR_SUMMARY, context_window * 20 // 100)
    return context_window - reserved


def _rough_token_count_estimation(content: str, chars_per_token: int = TEXT_CHARS_PER_TOKEN) -> int:
    return max(1, round(len(content) / chars_per_token))


def _estimate_unknown_object_tokens(value: Any) -> int:
    return _rough_token_count_estimation(json.dumps(value or ""), JSON_CHARS_PER_TOKEN)


def _estimate_content_block_tokens(content: Any) -> int:
    if isinstance(content, str):
        return _rough_token_count_estimation(content)

    if not isinstance(content, list):
        return 0

    total = 0
    for block in content:
        if not isinstance(block, dict):
            total += _estimate_unknown_object_tokens(block)
            continue

        block_type = block.get("type")
        if block_type == "text":
            total += _rough_token_count_estimation(block.get("text", ""))
        elif block_type == "tool_use":
            total += (
                TOOL_BLOCK_OVERHEAD_TOKENS
                + _rough_token_count_estimation(block.get("name", ""))
                + _estimate_unknown_object_tokens(block.get("input"))
            )
        elif block_type == "tool_result":
            serialized = block.get("content", "")
            if not isinstance(serialized, str):
                serialized = json.dumps(serialized)
            total += TOOL_BLOCK_OVERHEAD_TOKENS + _rough_token_count_estimation(serialized, JSON_CHARS_PER_TOKEN)
        elif block_type in ("image", "document"):
            total += FIXED_BINARY_BLOCK_TOKENS
        else:
            total += _estimate_unknown_object_tokens(block)

    return total


def estimate_message_tokens(message: dict[str, Any]) -> int:
    return MESSAGE_OVERHEAD_TOKENS + _estimate_content_block_tokens(message.get("content", ""))


def rough_token_count_estimation_for_messages(messages: list[dict[str, Any]]) -> int:
    raw_estimate = sum(estimate_message_tokens(m) for m in messages)
    return (raw_estimate * 4 + 2) // 3


def estimate_system_prompt_tokens(system_prompt: str) -> int:
    return _rough_token_count_estimation(system_prompt) + MESSAGE_OVERHEAD_TOKENS


def get_token_count_from_usage(usage: Usage) -> int:
    return (
        usage.input_tokens
        + (usage.cache_creation_input_tokens or 0)
        + (usage.cache_read_input_tokens or 0)
        + usage.output_tokens
    )


def token_count_with_estimation(
    messages: list[dict[str, Any]],
    *,
    usage: Usage | None = None,
    usage_anchor_index: int | None = None,
    system_prompt: str | None = None,
) -> int:
    system_prompt_tokens = estimate_system_prompt_tokens(system_prompt) if system_prompt else 0

    if usage and usage_anchor_index is not None and usage_anchor_index >= 0:
        suffix = messages[usage_anchor_index + 1 :]
        return get_token_count_from_usage(usage) + rough_token_count_estimation_for_messages(suffix) + system_prompt_tokens

    return rough_token_count_estimation_for_messages(messages) + system_prompt_tokens


class TokenBudgetSnapshot:
    def __init__(
        self,
        estimated_conversation_tokens: int,
        context_window: int,
        effective_context_window: int,
        auto_compact_threshold: int,
        manual_compact_threshold: int,
    ) -> None:
        self.estimated_conversation_tokens = estimated_conversation_tokens
        self.context_window = context_window
        self.effective_context_window = effective_context_window
        self.auto_compact_threshold = auto_compact_threshold
        self.manual_compact_threshold = manual_compact_threshold


def _scale_buffer(buffer: int, effective_window: int) -> int:
    reference_window = 180_000
    if effective_window >= reference_window:
        return buffer
    return round(buffer * effective_window / reference_window)


def build_token_budget_snapshot(
    messages: list[dict[str, Any]],
    *,
    usage: Usage | None = None,
    usage_anchor_index: int | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
) -> TokenBudgetSnapshot:
    estimated_conversation_tokens = token_count_with_estimation(
        messages, usage=usage, usage_anchor_index=usage_anchor_index, system_prompt=system_prompt
    )
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    context_window = get_context_window_for_model(model)
    effective_context_window = get_effective_context_window_size(model)
    return TokenBudgetSnapshot(
        estimated_conversation_tokens=estimated_conversation_tokens,
        context_window=context_window,
        effective_context_window=effective_context_window,
        auto_compact_threshold=max(0, effective_context_window - _scale_buffer(AUTOCOMPACT_BUFFER_TOKENS, effective_context_window)),
        manual_compact_threshold=max(0, effective_context_window - _scale_buffer(MANUAL_COMPACT_BUFFER_TOKENS, effective_context_window)),
    )
