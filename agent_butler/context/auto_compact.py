from __future__ import annotations

from typing import Any

from ..utils.tokens import (
    AUTOCOMPACT_BUFFER_TOKENS,
    MANUAL_COMPACT_BUFFER_TOKENS,
    WARNING_THRESHOLD_BUFFER_TOKENS,
    build_token_budget_snapshot,
    get_context_window_for_model,
    get_effective_context_window_size,
    rough_token_count_estimation_for_messages,
)

MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

STATES = ("normal", "warning", "blocking")

_consecutive_auto_compact_failures = 0


def reset_auto_compact_failures() -> None:
    global _consecutive_auto_compact_failures
    _consecutive_auto_compact_failures = 0


def _scale_buffer(buffer: int, effective_window: int) -> int:
    reference_window = 180_000
    if effective_window >= reference_window:
        return buffer
    return round(buffer * effective_window / reference_window)


def get_auto_compact_threshold(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(AUTOCOMPACT_BUFFER_TOKENS, effective))


def get_blocking_limit(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(MANUAL_COMPACT_BUFFER_TOKENS, effective))


def get_warning_threshold(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(WARNING_THRESHOLD_BUFFER_TOKENS, effective))


def check_auto_compact(messages: list[dict], usage: Any, model: str) -> str:
    global _consecutive_auto_compact_failures

    estimated_tokens = rough_token_count_estimation_for_messages(messages)
    blocking_limit = get_blocking_limit(model)
    auto_threshold = get_auto_compact_threshold(model)
    warning_threshold = get_warning_threshold(model)

    if estimated_tokens >= blocking_limit:
        return "blocking"
    if estimated_tokens >= auto_threshold:
        return "blocking"
    if estimated_tokens >= warning_threshold:
        return "warning"
    return "normal"


def should_auto_compact(estimated_tokens: int, model: str, query_source: str | None = None) -> bool:
    global _consecutive_auto_compact_failures
    if query_source in ("compact", "session_memory"):
        return False
    if _consecutive_auto_compact_failures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
        return False
    return estimated_tokens >= get_auto_compact_threshold(model)
