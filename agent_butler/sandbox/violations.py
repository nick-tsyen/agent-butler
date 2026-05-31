from __future__ import annotations

import re

SANDBOX_VIOLATION_INDICATORS = [
    "Operation not permitted",
    "operation not permitted",
    "sandbox-exec:",
    "deny file-write",
    "deny network-outbound",
    "EPERM",
    "EACCES",
]

VIOLATION_TAG_RE = re.compile(r"<sandbox_violations>[\s\S]*?</sandbox_violations>", re.DOTALL)


def looks_like_sandbox_violation(stderr: str) -> bool:
    return any(indicator in stderr for indicator in SANDBOX_VIOLATION_INDICATORS)


def annotate_stderr_with_sandbox_failures(stderr: str, exit_code: int | None) -> str:
    if exit_code is None or exit_code == 0:
        return stderr
    if not looks_like_sandbox_violation(stderr):
        return stderr
    if "<sandbox_violations>" in stderr:
        return stderr
    return stderr + "\n<sandbox_violations>possible sandbox denial detected</sandbox_violations>\n"


def remove_sandbox_violation_tags(text: str) -> str:
    return VIOLATION_TAG_RE.sub("", text)


def has_sandbox_violation_tag(text: str) -> bool:
    return "<sandbox_violations>" in text
