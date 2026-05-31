from __future__ import annotations

import json
import os
from typing import Any

from ..services.api.streaming import StreamRequestParams, create_message
from ..utils.log import debug_log
from ..utils.tokens import build_token_budget_snapshot

OLD_TOOL_RESULT_PLACEHOLDER = "[Old tool result content cleared]"
MICROCOMPACT_MIN_MESSAGES = 10
MICROCOMPACT_KEEP_RECENT_MESSAGES = 8
COMPACTABLE_TOOLS = {"Read", "Grep", "Glob", "Bash", "Edit", "Write"}

NO_TOOLS_PREAMBLE = (
    "CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.\n\n"
    "- Do NOT use Read, Bash, Grep, Glob, Edit, Write, or ANY other tool.\n"
    "- You already have all the context you need in the conversation above.\n"
    "- Tool calls will be REJECTED and will waste your only turn — you will fail the task.\n"
    "- Your entire response must be plain text: an <analysis> block followed by a <summary> block.\n"
)

DETAILED_ANALYSIS_INSTRUCTION_BASE = (
    "Before providing your final summary, wrap your analysis in <analysis> tags to organize your thoughts "
    "and ensure you've covered all necessary points. In your analysis process:\n\n"
    "1. Chronologically analyze each message and section of the conversation. For each section thoroughly identify:\n"
    "   - The user's explicit requests and intents\n"
    "   - Your approach to addressing the user's requests\n"
    "   - Key decisions, technical concepts and code patterns\n"
    "   - Specific details like:\n"
    "     - file names\n"
    "     - full code snippets\n"
    "     - function signatures\n"
    "     - file edits\n"
    "   - Errors that you ran into and how you fixed them\n"
    "   - Pay special attention to specific user feedback that you received, especially if the user told you to do something differently.\n"
    "2. Double-check for technical accuracy and completeness, addressing each required element thoroughly."
)

BASE_COMPACT_PROMPT = (
    "Your task is to create a detailed summary of the conversation so far, paying close attention to the user's "
    "explicit requests and your previous actions.\n"
    "This summary should be thorough in capturing technical details, code patterns, and architectural decisions "
    "that would be essential for continuing development work without losing context.\n\n"
    f"{DETAILED_ANALYSIS_INSTRUCTION_BASE}\n\n"
    "Your summary should include the following sections:\n\n"
    "1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail\n"
    "2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed.\n"
    "3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created. "
    "Pay special attention to the most recent messages and include full code snippets where applicable and "
    "include a summary of why this file read or edit is important.\n"
    "4. Errors and fixes: List all errors that you ran into, and how you fixed them. Pay special attention to "
    "specific user feedback that you received, especially if the user told you to do something differently.\n"
    "5. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.\n"
    "6. All user messages: List ALL user messages that are not tool results. These are critical for understanding "
    "the users' feedback and changing intent.\n"
    "7. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on.\n"
    "8. Current Work: Describe in detail precisely what was being worked on immediately before this summary request, "
    "paying special attention to the most recent messages from both user and assistant. Include file names and code "
    "snippets where applicable.\n"
    "9. Optional Next Step: List the next step that you will take that is related to the most recent work you were doing.\n\n"
    "Please provide your summary based on the conversation so far, following this structure and ensuring precision "
    "and thoroughness in your response."
)


def _is_content_blocks(content: Any) -> bool:
    return isinstance(content, list)


def _collect_tool_ids_from_message(message: dict) -> list[str]:
    content = message.get("content")
    if not _is_content_blocks(content):
        return []
    return [block["id"] for block in content if isinstance(block, dict) and block.get("type") == "tool_use"]


def _collect_tool_result_ids_from_message(message: dict) -> list[str]:
    content = message.get("content")
    if not _is_content_blocks(content):
        return []
    return [block["tool_use_id"] for block in content if isinstance(block, dict) and block.get("type") == "tool_result"]


def _micro_compact_tool_result_content(content: Any) -> str | None:
    if isinstance(content, list):
        if all(isinstance(b, dict) and b.get("type") in ("image", "document") for b in content):
            return "[image]"
    return None


def _micro_compact_message(message: dict) -> tuple[dict, list[str]]:
    content = message.get("content")
    if not _is_content_blocks(content):
        return message, []

    compacted_tool_ids: list[str] = []
    next_content = []

    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            next_content.append(block)
            continue

        binary_replacement = _micro_compact_tool_result_content(block.get("content"))
        if binary_replacement:
            compacted_tool_ids.append(block["tool_use_id"])
            next_content.append({**block, "content": binary_replacement})
            continue

        block_content = block.get("content")
        if not isinstance(block_content, str):
            next_content.append(block)
            continue

        colon_idx = block_content.find(":")
        tool_name = block_content[:colon_idx] if colon_idx > 0 else None
        if tool_name and tool_name in COMPACTABLE_TOOLS:
            compacted_tool_ids.append(block["tool_use_id"])
            next_content.append({**block, "content": OLD_TOOL_RESULT_PLACEHOLDER})
        else:
            next_content.append(block)

    return {**message, "content": next_content}, compacted_tool_ids


def micro_compact_messages(messages: list[dict]) -> tuple[list[dict], list[str]]:
    if len(messages) < MICROCOMPACT_MIN_MESSAGES:
        return messages, []

    all_compacted_tool_ids: list[str] = []
    next_messages = []

    for i, message in enumerate(messages):
        if i >= len(messages) - MICROCOMPACT_KEEP_RECENT_MESSAGES:
            next_messages.append(message)
        else:
            compacted_msg, tool_ids = _micro_compact_message(message)
            next_messages.append(compacted_msg)
            all_compacted_tool_ids.extend(tool_ids)

    return next_messages, all_compacted_tool_ids


def _make_compact_boundary(
    compact_type: str,
    original_message_count: int,
    reason: str | None = None,
    compacted_tool_ids: list[str] | None = None,
) -> dict:
    parts = [
        "[CompactBoundary]",
        f"type={compact_type}",
        f"messages={original_message_count}",
    ]
    if reason:
        parts.append(f"reason={reason}")
    if compacted_tool_ids:
        parts.append(f"compacted_tool_ids={','.join(compacted_tool_ids)}")
    return {"role": "assistant", "content": " ".join(parts)}


def get_messages_after_compact_boundary(messages: list[dict]) -> list[dict]:
    for i in range(len(messages) - 1, -1, -1):
        content = messages[i].get("content", "")
        if isinstance(content, str) and content.startswith("[CompactBoundary]"):
            return messages[i + 1:]
    return messages


def _find_preserved_tail_start(messages: list[dict], desired_count: int) -> int:
    start = max(0, len(messages) - desired_count)

    while start > 0:
        tail = messages[start:]
        tool_uses = set()
        tool_results = set()
        for msg in tail:
            tool_uses.update(_collect_tool_ids_from_message(msg))
            tool_results.update(_collect_tool_result_ids_from_message(msg))
        has_dangling = any(tid not in tool_uses for tid in tool_results)
        if not has_dangling:
            return start
        start -= 1

    return 0


async def _summarize_messages(messages: list[dict], focus: str | None = None) -> str:
    extra_instruction = f"\n\n## Compact Instructions\n{focus}" if focus else ""
    debug_log("compact", "summary_request", {"messageCount": len(messages), "focus": focus})

    response = await create_message(StreamRequestParams(
        model=os.environ.get("ANTHROPIC_MODEL"),
        max_tokens=8000,
        system=NO_TOOLS_PREAMBLE + BASE_COMPACT_PROMPT + extra_instruction,
        messages=[{
            "role": "user",
            "content": f"Conversation to summarize:\n{json.dumps(messages, indent=2)}",
        }],
    ))

    text_parts = [
        block.text for block in response["content"]
        if hasattr(block, "type") and block.type == "text"
    ]
    text = "\n".join(text_parts).strip()

    debug_log("compact", "summary_response", {
        "stopReason": response["stop_reason"],
        "summaryLength": len(text),
    })

    return text


async def compact_conversation(messages: list[dict], model: str) -> list[dict]:
    micro_compacted, compacted_tool_ids = micro_compact_messages(messages)

    result = await _summarize_messages(micro_compacted)

    desired_tail_count = 8
    tail_start = (
        len(micro_compacted)
        if len(micro_compacted) <= desired_tail_count
        else _find_preserved_tail_start(micro_compacted, desired_tail_count)
    )
    tail = micro_compacted[tail_start:]

    summary_header = (
        "This session is being continued from a previous conversation that ran out of context. "
        "The summary below covers the earlier portion of the conversation."
    )
    tail_note = "\n\nRecent messages are preserved verbatim." if tail else ""

    return [
        {"role": "user", "content": f"{summary_header}\n\n{result}{tail_note}"},
        _make_compact_boundary(
            compact_type="auto",
            original_message_count=len(micro_compacted),
            compacted_tool_ids=compacted_tool_ids,
        ),
        *tail,
    ]
