from __future__ import annotations

PLAN_ATTACHMENT_MARKER = "[plan_mode_attachment]"
PLAN_EXIT_MARKER = "[plan_mode_exit]"

TURNS_BETWEEN_ATTACHMENTS = 5
FULL_REMINDER_EVERY_N = 5


def get_plan_attachments() -> list[str]:
    return []


def _build_full_plan_mode_text(plan_file_path: str) -> str:
    return "\n".join([
        PLAN_ATTACHMENT_MARKER,
        "",
        "PLAN MODE ACTIVE — You are currently in plan mode.",
        "",
        "Workflow:",
        "1. EXPLORE: Use Read, Grep, Glob, and read-only Bash commands (ls, cat, git status, etc.) to understand the codebase.",
        "2. PLAN: Write a detailed implementation plan to the plan file using the structure below.",
        "3. EXIT: Call ExitPlanMode with a summary and any allowedPrompts for auto-approved commands.",
        "",
        "Plan file structure (write to the plan file using this format):",
        "",
        "## Context",
        "Begin with a Context section: what is the problem, what does the user need, what is the expected outcome.",
        "",
        "## Recommended approach",
        "Describe your recommended approach concisely but with enough detail to be executable.",
        "",
        "## Critical files",
        "List the paths of critical files that will be created or modified.",
        "",
        "## Reuse",
        "Identify existing functions, utilities, or patterns in the codebase that should be reused, with paths.",
        "",
        "## Verification",
        "Describe how to test and verify the implementation end-to-end.",
        "",
        "Rules:",
        "- Do NOT use Edit or destructive Bash commands.",
        "- Do NOT use Write on any file except the plan file below.",
        "- Do NOT ask the user for approval via text — use ExitPlanMode when ready.",
        "- You MUST end your turn by either continuing exploration or calling ExitPlanMode.",
        "",
        f"Plan file: {plan_file_path}",
    ])


def _build_sparse_plan_mode_text(plan_file_path: str) -> str:
    return "\n".join([
        PLAN_ATTACHMENT_MARKER,
        "",
        "Reminder: You are still in PLAN MODE. Only read-only tools are allowed.",
        f"Write your plan to: {plan_file_path}",
        "Call ExitPlanMode when your plan is ready.",
    ])


def _build_plan_mode_exit_text(plan_file_path: str, plan_exists: bool) -> str:
    lines = [
        PLAN_EXIT_MARKER,
        "",
        "You have exited plan mode. Full tool access is now restored.",
    ]
    if plan_exists:
        lines.append(
            f"Your approved plan is at: {plan_file_path}",
            "Proceed with implementing the plan. You may now use Edit, Write, Bash, and all other tools.",
        )
    return "\n".join(lines)


def _is_attachment_message(msg: dict) -> bool:
    content = msg.get("content", "")
    if not isinstance(content, str):
        return False
    return PLAN_ATTACHMENT_MARKER in content or PLAN_EXIT_MARKER in content


def _count_human_turns_since_last_attachment(messages: list[dict]) -> int:
    count = 0
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        if _is_attachment_message(msg):
            return count
        if isinstance(msg.get("content"), str):
            count += 1
    return count


def _count_plan_attachments_since_last_exit(messages: list[dict]) -> int:
    count = 0
    for msg in reversed(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), str):
            continue
        if PLAN_EXIT_MARKER in msg["content"]:
            break
        if PLAN_ATTACHMENT_MARKER in msg["content"]:
            count += 1
    return count


def get_plan_mode_attachment(
    messages: list[dict],
    plan_file_path: str,
) -> dict | None:
    turns_since = _count_human_turns_since_last_attachment(messages)

    has_any = any(
        m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and PLAN_ATTACHMENT_MARKER in m["content"]
        for m in messages
    )
    if not has_any:
        return {"role": "user", "content": _build_full_plan_mode_text(plan_file_path)}

    if turns_since < TURNS_BETWEEN_ATTACHMENTS:
        return None

    attachment_count = _count_plan_attachments_since_last_exit(messages) + 1
    is_full = attachment_count % FULL_REMINDER_EVERY_N == 1

    text = (
        _build_full_plan_mode_text(plan_file_path)
        if is_full
        else _build_sparse_plan_mode_text(plan_file_path)
    )
    return {"role": "user", "content": text}


def get_plan_mode_exit_attachment(plan_file_path: str, plan_exists: bool) -> dict:
    return {"role": "user", "content": _build_plan_mode_exit_text(plan_file_path, plan_exists)}
