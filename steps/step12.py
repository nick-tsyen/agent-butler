"""
Step 12 - Token budget management: multi-tier thresholds, circuit breaker,
          tool result truncation, and output token optimization

Goal:
- parameterize context window by model (+ env override)
- adaptive buffer scaling for small windows
- four-state warning system: normal → warning → error → blocking
- circuit breaker to stop retrying failed auto-compaction
- escape condition to prevent compaction-triggers-compaction loops
- truncate oversized tool results before they enter the message history
- split max_tokens into three tiers (daily / retry / compact)
- invalidate usage anchor after compaction to avoid stale estimates

Builds on step11.py — token estimation and compaction primitives are imported.
"""

from __future__ import annotations

import os
from typing import Any, Awaitable, Callable

from .step11 import (
    compact_messages,
    estimate_messages_tokens,
    micro_compact_messages,
    token_count_with_estimation,
)

# ── Model context window ───────────────────────────────────────────────────────

MODEL_CONTEXT_WINDOW_DEFAULT: int = 200_000
MAX_OUTPUT_TOKENS_FOR_SUMMARY: int = 20_000

# Known model context windows; add new models here as they are released.
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
}


def get_context_window_for_model(model: str) -> int:
    """
    Return the context window for *model*, respecting the env override.

    The ``CLAUDE_CODE_MAX_CONTEXT_TOKENS`` environment variable can override
    the window for any model, which is useful for testing with small windows.
    """
    env_override = os.environ.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS")
    if env_override:
        try:
            parsed = int(env_override)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOW_DEFAULT)


def get_effective_context_window_size(model: str) -> int:
    """
    Effective window = context window minus space reserved for summary output.

    For small windows (<100K) we use 20% instead of a fixed 20K to avoid
    the reserved portion exceeding the window itself.
    """
    context_window = get_context_window_for_model(model)
    reserved = min(MAX_OUTPUT_TOKENS_FOR_SUMMARY, context_window // 5)
    return context_window - reserved


# ── Adaptive buffer scaling ────────────────────────────────────────────────────

AUTOCOMPACT_BUFFER_TOKENS: int = 13_000
WARNING_THRESHOLD_BUFFER_TOKENS: int = 20_000
MANUAL_COMPACT_BUFFER_TOKENS: int = 3_000
REFERENCE_WINDOW: int = 180_000


def _scale_buffer(buffer: int, effective_window: int) -> int:
    """
    Scale the buffer proportionally when effective window < 180K.

    A 30K window gets roughly 30/180 ≈ 17% of the original buffer,
    keeping the trigger ratio consistent across window sizes.
    """
    if effective_window >= REFERENCE_WINDOW:
        return buffer
    return round(buffer * (effective_window / REFERENCE_WINDOW))


def _get_auto_compact_threshold(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(AUTOCOMPACT_BUFFER_TOKENS, effective))


def _get_blocking_limit(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(MANUAL_COMPACT_BUFFER_TOKENS, effective))


def _get_warning_threshold(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return max(0, effective - _scale_buffer(WARNING_THRESHOLD_BUFFER_TOKENS, effective))


# ── Four-state warning system ─────────────────────────────────────────────────


def calculate_token_warning_state(
    estimated_tokens: int, model: str
) -> dict[str, Any]:
    """
    Return the current warning state given estimated token usage.

    States in order of severity: normal → warning → error → blocking.
    """
    context_window = get_context_window_for_model(model)
    blocking_limit = _get_blocking_limit(model)
    auto_compact_threshold = _get_auto_compact_threshold(model)
    warning_threshold = _get_warning_threshold(model)

    if estimated_tokens >= blocking_limit:
        state = "blocking"
    elif estimated_tokens >= auto_compact_threshold:
        state = "error"
    elif estimated_tokens >= warning_threshold:
        state = "warning"
    else:
        state = "normal"

    return {
        "state": state,
        "estimated_tokens": estimated_tokens,
        "threshold": auto_compact_threshold,
        "blocking_limit": blocking_limit,
        "context_window": context_window,
    }


# ── Circuit breaker ────────────────────────────────────────────────────────────

MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES: int = 3

# Module-level mutable counter — intentional for teaching simplicity.
_consecutive_auto_compact_failures: int = 0


def reset_auto_compact_failures() -> None:
    """Reset the circuit breaker counter after a successful compaction."""
    global _consecutive_auto_compact_failures
    _consecutive_auto_compact_failures = 0


def should_auto_compact(
    estimated_tokens: int,
    model: str,
    query_source: str | None = None,
) -> bool:
    """
    Decide whether auto-compaction should fire.

    Returns False when:
    1. The request itself is a compaction call (escape condition).
    2. Circuit breaker is open (too many consecutive failures).
    3. Token usage is below the threshold.
    """
    global _consecutive_auto_compact_failures

    # Escape condition: don't compact inside a compact call.
    if query_source in ("compact", "session_memory"):
        return False

    # Circuit breaker: stop retrying after repeated failures.
    if _consecutive_auto_compact_failures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
        return False

    return estimated_tokens >= _get_auto_compact_threshold(model)


async def auto_compact_if_needed(
    messages: list[dict[str, Any]],
    model: str,
    call_model: Callable[[str, list[dict[str, Any]]], Awaitable[str]],
    *,
    usage: dict[str, int] | None = None,
    usage_anchor_index: int | None = None,
    query_source: str | None = None,
) -> dict[str, Any]:
    """
    Run auto-compaction if token usage exceeds the threshold.

    Increments the circuit-breaker counter on failure; resets it on success.
    """
    global _consecutive_auto_compact_failures

    estimated_tokens = token_count_with_estimation(
        messages, usage=usage, usage_anchor_index=usage_anchor_index
    )

    if not should_auto_compact(estimated_tokens, model, query_source):
        return {
            "result": {"messages": messages, "did_compact": False, "did_micro_compact": False},
            "did_auto_compact": False,
        }

    try:
        result = await compact_messages(
            messages,
            call_model,
            force=True,
            usage=usage,
            usage_anchor_index=usage_anchor_index,
        )
        _consecutive_auto_compact_failures = 0
        return {"result": result, "did_auto_compact": result["did_compact"]}
    except Exception:
        _consecutive_auto_compact_failures += 1
        return {
            "result": {"messages": messages, "did_compact": False, "did_micro_compact": False},
            "did_auto_compact": False,
        }


# ── Tool result truncation ────────────────────────────────────────────────────

DEFAULT_MAX_RESULT_SIZE_CHARS: int = 100_000


def truncate_tool_result(content: str, max_chars: int = DEFAULT_MAX_RESULT_SIZE_CHARS) -> str:
    """
    Truncate an oversized tool result before it enters message history.

    A truncation notice is appended so the model knows the output was cut.
    """
    if len(content) <= max_chars:
        return content
    truncated = content[:max_chars]
    return f"{truncated}\n\n[Output truncated: {len(content)} chars total, showing first {max_chars}]"


# ── Output token tiers ────────────────────────────────────────────────────────

CAPPED_DEFAULT_MAX_TOKENS: int = 8_000    # Normal requests
ESCALATED_MAX_TOKENS: int = 64_000        # Retry after truncation
COMPACT_MAX_OUTPUT_TOKENS: int = 20_000   # Compaction summary


async def stream_message_with_retry(
    call_model: Callable[[list[dict[str, Any]], dict[str, Any]], Awaitable[dict[str, Any]]],
    messages: list[dict[str, Any]],
    *,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """
    Simulates the truncation-recovery flow:
    1. Send request with 8K max_tokens.
    2. If response is truncated (stop_reason == "max_tokens"), retry with 64K.
    """
    effective_max = max_tokens if max_tokens is not None else CAPPED_DEFAULT_MAX_TOKENS
    result = await call_model(messages, {"max_tokens": effective_max})

    if result.get("stop_reason") == "max_tokens" and effective_max < ESCALATED_MAX_TOKENS:
        return await call_model(messages, {"max_tokens": ESCALATED_MAX_TOKENS})

    return result


# ── Usage anchor invalidation ─────────────────────────────────────────────────


class UsageAnchor:
    """
    Manages the usage anchor lifecycle.

    After compaction the message array is restructured; the old anchor
    index and usage become stale. Failing to invalidate causes
    token_count_with_estimation to return pre-compaction values, which
    triggers an immediate re-compaction loop.
    """

    def __init__(self) -> None:
        self.index: int = -1
        self.usage: dict[str, int] | None = None

    def update(self, index: int, usage: dict[str, int]) -> None:
        """Record a new anchor from a fresh API response."""
        self.index = index
        self.usage = usage

    def invalidate(self) -> None:
        """Reset the anchor after compaction or other structural changes."""
        self.index = -1
        self.usage = None

    def get_estimation_options(self) -> dict[str, Any]:
        """Return keyword args suitable for token_count_with_estimation."""
        if self.index < 0 or self.usage is None:
            return {}
        return {"usage": self.usage, "usage_anchor_index": self.index}


# ── MicroCompact enhancements (v2) ────────────────────────────────────────────

COMPACTABLE_TOOLS_V2: frozenset[str] = frozenset(["Read", "Grep", "Glob", "Bash", "Edit", "Write"])


def _micro_compact_tool_result_content(content: Any) -> str | None:
    """
    Detect binary-only content blocks (images, documents) in tool results
    and return a lightweight placeholder string, or None if not applicable.
    """
    if isinstance(content, list):
        if all(b.get("type") in ("image", "document") for b in content):
            return "[image]"
    return None


def micro_compact_message_v2(
    message: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """
    Enhanced micro-compaction that also handles binary content blocks.

    Extends the basic version from step11.py to cover image/document
    tool results and a larger set of compactable tool names.
    """
    import re

    if not isinstance(message.get("content"), list):
        return message, False

    cleared = False
    new_content = []

    for block in message["content"]:
        if block.get("type") != "tool_result":
            new_content.append(block)
            continue

        # Handle binary content blocks (image, document).
        binary_replacement = _micro_compact_tool_result_content(block.get("content"))
        if binary_replacement:
            cleared = True
            new_content.append({**block, "content": binary_replacement})
            continue

        if not isinstance(block.get("content"), str):
            new_content.append(block)
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):", block["content"])
        tool_name = match.group(1) if match else None

        if tool_name and tool_name in COMPACTABLE_TOOLS_V2:
            cleared = True
            new_content.append({**block, "content": "[Old tool result content cleared]"})
        else:
            new_content.append(block)

    return {**message, "content": new_content}, cleared


# ── Compact message filtering (UI) ────────────────────────────────────────────


def is_compact_message(message: dict[str, Any]) -> bool:
    """
    Return True when *message* is a compaction boundary or summary message.

    UI components use this to hide compaction artefacts from the user.
    """
    content = message.get("content", "")
    if not isinstance(content, str):
        return False
    return content.startswith("[CompactBoundary]") or content.startswith(
        "This session is being continued from a previous conversation"
    )


# ── Demo ──────────────────────────────────────────────────────────────────────


def _run_demo() -> None:
    import os as _os

    model = "claude-sonnet-4-20250514"

    print("=== Model Context Window ===")
    print(f"Default window: {get_context_window_for_model(model)}")
    print(f"Effective window: {get_effective_context_window_size(model)}")

    print("\n=== Threshold System (200K window) ===")
    print(f"  Warning threshold:     {_get_warning_threshold(model)}")
    print(f"  AutoCompact threshold: {_get_auto_compact_threshold(model)}")
    print(f"  Blocking limit:        {_get_blocking_limit(model)}")

    small_model = "test-small"
    _os.environ["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = "30000"
    print("\n=== Threshold System (30K window, env override) ===")
    print(f"  Context window:        {get_context_window_for_model(small_model)}")
    print(f"  Effective window:      {get_effective_context_window_size(small_model)}")
    print(f"  Warning threshold:     {_get_warning_threshold(small_model)}")
    print(f"  AutoCompact threshold: {_get_auto_compact_threshold(small_model)}")
    print(f"  Blocking limit:        {_get_blocking_limit(small_model)}")
    del _os.environ["CLAUDE_CODE_MAX_CONTEXT_TOKENS"]

    print("\n=== Warning State Transitions ===")
    for tokens in [150_000, 162_000, 170_000, 179_000]:
        result = calculate_token_warning_state(tokens, model)
        pct = round(tokens / result["context_window"] * 100)
        print(f"  {tokens} tokens ({pct}%) → {result['state']}")

    print("\n=== Circuit Breaker ===")
    reset_auto_compact_failures()
    print(f"  Should compact at 170K: {should_auto_compact(170_000, model)}")

    global _consecutive_auto_compact_failures
    _consecutive_auto_compact_failures = 3
    print(f"  After 3 failures:      {should_auto_compact(170_000, model)} (circuit open)")
    reset_auto_compact_failures()
    print(f"  After reset:           {should_auto_compact(170_000, model)}")

    print("\n=== Escape Condition ===")
    print(f"  query_source='compact': {should_auto_compact(170_000, model, 'compact')}")
    print(f"  query_source=None:      {should_auto_compact(170_000, model)}")

    print("\n=== Tool Result Truncation ===")
    long_output = "x" * 200_000
    truncated = truncate_tool_result(long_output)
    print(f"  Input:  {len(long_output)} chars")
    print(f"  Output: {len(truncated)} chars")
    print(f"  Ends with: ...{truncated[-60:]}")

    print("\n=== Output Token Tiers ===")
    print(f"  Daily:   {CAPPED_DEFAULT_MAX_TOKENS}")
    print(f"  Retry:   {ESCALATED_MAX_TOKENS}")
    print(f"  Compact: {COMPACT_MAX_OUTPUT_TOKENS}")

    print("\n=== Usage Anchor Invalidation ===")
    anchor = UsageAnchor()
    anchor.update(15, {"input_tokens": 50_000, "output_tokens": 2_000})
    print(f"  After update: index={anchor.index}", anchor.get_estimation_options())
    anchor.invalidate()
    print(f"  After invalidate: index={anchor.index}", anchor.get_estimation_options())

    print("\n=== MicroCompact V2: binary content ===")
    msg_with_image = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": [{"type": "image", "source": "..."}],
            }
        ],
    }
    compacted_msg, was_cleared = micro_compact_message_v2(msg_with_image)
    print(f"  Cleared: {was_cleared}")
    print(f"  Result:  {compacted_msg['content'][0]['content']!r}")

    print("\n=== Compact Message Filter ===")
    print(f"  Boundary:  {is_compact_message({'content': '[CompactBoundary] type=auto'})}")
    print(
        f"  Summary:   "
        f"{is_compact_message({'content': 'This session is being continued from a previous conversation...'})}"
    )
    print(f"  Normal:    {is_compact_message({'content': 'Hello world'})}")


if __name__ == "__main__":
    _run_demo()
