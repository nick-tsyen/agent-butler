"""
Step 11 - Context compaction: token estimation, micro-compact, and full summarization

Goal:
- estimate token usage with char-based heuristics + API usage anchor
- micro-compact old tool results (zero API cost)
- full compact via AI-generated summary when over threshold
- preserve tool_use / tool_result pairing across compaction
- support /compact with optional focus instructions

This file distills the core compaction logic into a self-contained learning module.
"""

from __future__ import annotations

import json
import math
from typing import Any, Awaitable, Callable

# ── Token estimation constants ─────────────────────────────────────────────────

TEXT_CHARS_PER_TOKEN: int = 4
JSON_CHARS_PER_TOKEN: int = 2
MESSAGE_OVERHEAD_TOKENS: int = 12
TOOL_BLOCK_OVERHEAD_TOKENS: int = 24
FIXED_BINARY_BLOCK_TOKENS: int = 2_000

MODEL_CONTEXT_WINDOW: int = 200_000
AUTOCOMPACT_BUFFER_TOKENS: int = 13_000


# ── Token counting ─────────────────────────────────────────────────────────────


def rough_token_count(content: str, chars_per_token: int = TEXT_CHARS_PER_TOKEN) -> int:
    """Estimate token count from character count using a fixed ratio."""
    return max(1, round(len(content) / chars_per_token))


def estimate_content_block_tokens(content: Any) -> int:
    """
    Estimate the tokens consumed by a message's content field.

    Handles both string content and lists of content blocks (text, tool_use,
    tool_result, image, document).
    """
    if isinstance(content, str):
        return rough_token_count(content)

    if not isinstance(content, list):
        return 0

    total = 0
    for block in content:
        block_type = block.get("type", "")
        if block_type == "text":
            total += rough_token_count(block.get("text", ""))
        elif block_type == "tool_use":
            total += TOOL_BLOCK_OVERHEAD_TOKENS
            total += rough_token_count(block.get("name", ""))
            total += rough_token_count(
                json.dumps(block.get("input") or {}), JSON_CHARS_PER_TOKEN
            )
        elif block_type == "tool_result":
            c = block.get("content", "")
            s = c if isinstance(c, str) else json.dumps(c)
            total += TOOL_BLOCK_OVERHEAD_TOKENS + rough_token_count(s, JSON_CHARS_PER_TOKEN)
        elif block_type in ("image", "document"):
            total += FIXED_BINARY_BLOCK_TOKENS
        else:
            total += rough_token_count(json.dumps(block), JSON_CHARS_PER_TOKEN)

    return total


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """Estimate the tokens consumed by a single message."""
    return MESSAGE_OVERHEAD_TOKENS + estimate_content_block_tokens(message.get("content", ""))


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """
    Estimate the total tokens consumed by a list of messages.

    Applies a conservative 33% upward correction to account for prompt
    formatting overhead not captured by the char-based heuristic.
    """
    raw = sum(estimate_message_tokens(m) for m in messages)
    return math.ceil((raw * 4) / 3)


def token_count_with_estimation(
    messages: list[dict[str, Any]],
    *,
    usage: dict[str, int] | None = None,
    usage_anchor_index: int | None = None,
) -> int:
    """
    Hybrid token estimation: use last API usage as anchor + estimate suffix.

    When we have a recent API response, its ``usage.input_tokens`` already
    reflects the exact token count of the full prompt at that point.
    We only need to estimate tokens for messages added *after* that point.
    """
    if usage is not None and usage_anchor_index is not None and usage_anchor_index >= 0:
        known_tokens = (
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("output_tokens", 0)
        )
        suffix = messages[usage_anchor_index + 1:]
        return known_tokens + estimate_messages_tokens(suffix)

    return estimate_messages_tokens(messages)


# ── Token budget snapshot ─────────────────────────────────────────────────────


def build_token_budget_snapshot(
    messages: list[dict[str, Any]],
    *,
    usage: dict[str, int] | None = None,
    usage_anchor_index: int | None = None,
) -> dict[str, int]:
    """Return a snapshot of the current token budget position."""
    estimated_tokens = token_count_with_estimation(
        messages, usage=usage, usage_anchor_index=usage_anchor_index
    )
    effective_window = MODEL_CONTEXT_WINDOW - 20_000
    return {
        "estimated_tokens": estimated_tokens,
        "context_window": MODEL_CONTEXT_WINDOW,
        "effective_window": effective_window,
        "auto_compact_threshold": effective_window - AUTOCOMPACT_BUFFER_TOKENS,
    }


# ── MicroCompact ───────────────────────────────────────────────────────────────

MICROCOMPACT_MIN_MESSAGES: int = 10
MICROCOMPACT_KEEP_RECENT: int = 8
COMPACTABLE_TOOLS: frozenset[str] = frozenset(["Read", "Grep", "Glob", "Bash"])
CLEARED_PLACEHOLDER: str = "[Old tool result content cleared]"


def _micro_compact_message(
    message: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """
    Replace old tool result content with a lightweight placeholder.

    Returns the (possibly modified) message and a boolean indicating
    whether any content was cleared.
    """
    if not isinstance(message.get("content"), list):
        return message, False

    cleared = False
    new_content = []

    for block in message["content"]:
        if block.get("type") != "tool_result" or not isinstance(block.get("content"), str):
            new_content.append(block)
            continue

        # Check if this result comes from a compactable tool by inspecting the
        # first word of the content string (tools prefix their output with the
        # tool name followed by a colon).
        import re
        match = re.match(r"^([A-Za-z0-9_-]+):", block["content"])
        tool_name = match.group(1) if match else None

        if tool_name and tool_name in COMPACTABLE_TOOLS:
            cleared = True
            new_content.append({**block, "content": CLEARED_PLACEHOLDER})
        else:
            new_content.append(block)

    return {**message, "content": new_content}, cleared


def micro_compact_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """
    Apply micro-compaction to messages older than the recent tail.

    Returns (compacted_messages, did_clear).  No API call is needed.
    """
    if len(messages) < MICROCOMPACT_MIN_MESSAGES:
        return messages, False

    did_clear = False
    result = []
    for i, msg in enumerate(messages):
        # Keep the most recent MICROCOMPACT_KEEP_RECENT messages untouched.
        if i >= len(messages) - MICROCOMPACT_KEEP_RECENT:
            result.append(msg)
        else:
            compacted, cleared = _micro_compact_message(msg)
            if cleared:
                did_clear = True
            result.append(compacted)

    return result, did_clear


# ── Tail preservation ─────────────────────────────────────────────────────────


def _find_safe_tail_start(messages: list[dict[str, Any]], desired_count: int) -> int:
    """
    Find a safe start index for the preserved tail.

    We must not split a tool_use / tool_result pair across the summary
    boundary — the API requires them to appear together in a conversation.
    """
    start = max(0, len(messages) - desired_count)

    while start > 0:
        tail = messages[start:]
        use_ids: set[str] = set()
        result_ids: set[str] = set()

        for msg in tail:
            if not isinstance(msg.get("content"), list):
                continue
            for block in msg["content"]:
                if block.get("type") == "tool_use":
                    use_ids.add(block["id"])
                if block.get("type") == "tool_result":
                    result_ids.add(block["tool_use_id"])

        # If any result references an id not in the tail's uses, back up.
        has_dangling = any(rid not in use_ids for rid in result_ids)
        if not has_dangling:
            return start
        start -= 1

    return 0


# ── Full compaction ────────────────────────────────────────────────────────────

COMPACT_SYSTEM_PROMPT: str = """CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

Your task is to create a detailed summary of the conversation so far.
Capture: user requests, technical decisions, file names, code snippets,
errors encountered, pending tasks, and what was being worked on most recently.

Wrap your analysis in <analysis> tags, then provide the final <summary>."""


async def compact_messages(
    messages: list[dict[str, Any]],
    call_model: Callable[[str, list[dict[str, Any]]], Awaitable[str]],
    *,
    force: bool = False,
    usage: dict[str, int] | None = None,
    usage_anchor_index: int | None = None,
) -> dict[str, Any]:
    """
    Full compaction: summarize history + keep recent tail.

    Args:
        messages:    The full conversation history.
        call_model:  Async callable ``(system, messages) -> summary_str``.
                     Abstracted so this module stays independent of any
                     specific API client.
        force:       Skip the threshold check and always compact.

    Returns a dict with keys:
        messages, summary (str|None), did_compact (bool), did_micro_compact (bool).
    """
    # Step 1: micro-compact first (free, no API call).
    micro_compacted, did_clear = micro_compact_messages(messages)

    # Step 2: check whether we're above the auto-compact threshold.
    budget = build_token_budget_snapshot(
        micro_compacted,
        usage=usage,
        usage_anchor_index=usage_anchor_index,
    )
    if not force and budget["estimated_tokens"] < budget["auto_compact_threshold"]:
        return {
            "messages": micro_compacted,
            "did_compact": False,
            "did_micro_compact": did_clear,
        }

    # Step 3: ask the model to summarize the conversation.
    summary = await call_model(
        COMPACT_SYSTEM_PROMPT,
        [
            {
                "role": "user",
                "content": f"Conversation to summarize:\n{json.dumps(micro_compacted, indent=2)}",
            }
        ],
    )

    # Step 4: build the compacted message list.
    tail_start = (
        len(micro_compacted)
        if len(micro_compacted) <= 8
        else _find_safe_tail_start(micro_compacted, 8)
    )
    tail = micro_compacted[tail_start:]

    continuation_parts = [
        "This session is being continued from a previous conversation that ran out of context.",
        f"The summary below covers the earlier portion of the conversation.\n\n{summary}",
    ]
    if tail:
        continuation_parts.append("Recent messages are preserved verbatim.")

    compacted = [
        {"role": "user", "content": " ".join(continuation_parts)},
        {
            "role": "assistant",
            "content": f"[CompactBoundary] type=auto messages={len(micro_compacted)}",
        },
        *tail,
    ]

    return {
        "messages": compacted,
        "summary": summary,
        "did_compact": True,
        "did_micro_compact": did_clear,
    }


# ── Demo ──────────────────────────────────────────────────────────────────────


def _run_demo() -> None:
    """Demonstrate token estimation and micro-compaction on synthetic data."""
    messages = []
    for i in range(15):
        messages.append({
            "role": "assistant",
            "content": [
                {"type": "text", "text": f"Looking at file {i}..."},
                {
                    "type": "tool_use",
                    "id": f"tool_{i}",
                    "name": "Read",
                    "input": {"file_path": f"src/file{i}.ts"},
                },
            ],
        })
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": f"tool_{i}",
                    "content": f"Read:{'x' * 500}",
                }
            ],
        })

    print("=== Token Estimation ===")
    print(f"Messages: {len(messages)}")
    print(f"Estimated tokens: {estimate_messages_tokens(messages)}")

    budget = build_token_budget_snapshot(messages)
    print(f"Auto-compact threshold: {budget['auto_compact_threshold']}")
    print(f"Over threshold: {budget['estimated_tokens'] >= budget['auto_compact_threshold']}")

    print("\n=== MicroCompact ===")
    micro, did_clear = micro_compact_messages(messages)
    print(f"Did clear: {did_clear}")

    old_tokens = estimate_messages_tokens(messages)
    new_tokens = estimate_messages_tokens(micro)
    saved_pct = round((1 - new_tokens / old_tokens) * 100)
    print(f"Before: {old_tokens} tokens → After: {new_tokens} tokens")
    print(f"Saved: {old_tokens - new_tokens} tokens ({saved_pct}%)")

    # Verify tool_use / tool_result pairing is preserved.
    pairs = sum(
        1
        for msg in micro
        if isinstance(msg.get("content"), list)
        for block in msg["content"]
        if block.get("type") == "tool_result"
    )
    print(f"Tool result blocks preserved: {pairs}")


if __name__ == "__main__":
    _run_demo()
