"""
Step 18 - Bash sandboxing

Goal:
- block dangerous shell operations in interactive mode
- auto-approve safe read-only commands
- run commands inside a Docker sandbox when enabled
- combine category-based rules with user-defined allow-list entries

This file shows the core decision logic; the actual Docker wiring lives
in agent-butler/src/sandbox/*.
"""

from __future__ import annotations

import os
import re
from typing import Any

# ── Category definitions ──────────────────────────────────────────────────────

SAFE_READ_ONLY_PREFIXES: list[str] = [
    "cat", "ls", "pwd", "echo", "find", "rg", "grep",
    "git diff", "git log", "git show", "git status",
    "head", "tail", "wc", "stat", "du", "df", "env",
    "which", "type", "date", "uname", "id", "whoami",
]

POTENTIALLY_DESTRUCTIVE_PREFIXES: list[str] = [
    "rm ", "sudo ", "chmod ", "chown ", "mv ",
    "dd ", "mkfs", "fdisk", "format",
    "curl ", "wget ", "nc ", "ncat ", "netcat ",
    "python -c", "python3 -c", "node -e",
    "> /",  # redirect to root
]

GIT_WRITE_PREFIXES: list[str] = [
    "git push", "git commit", "git reset --hard",
    "git force", "git branch -d", "git branch -D",
    "git rebase", "git cherry-pick",
]

# Combined blocklist consulted by check_sandbox_permission.
BLOCKED_PREFIXES: list[str] = [
    *POTENTIALLY_DESTRUCTIVE_PREFIXES,
    *GIT_WRITE_PREFIXES,
]


# ── Normalizer ────────────────────────────────────────────────────────────────


def _normalize(command: str) -> str:
    """Collapse whitespace and strip leading/trailing space."""
    return re.sub(r"\s+", " ", command.strip())


# ── Command classifiers ────────────────────────────────────────────────────────


def is_safe_read_only(command: str) -> bool:
    """Return True when *command* starts with a known safe prefix."""
    n = _normalize(command)
    return any(n == p or n.startswith(p + " ") for p in SAFE_READ_ONLY_PREFIXES)


def is_blocked(command: str) -> bool:
    """Return True when *command* starts with a known destructive prefix."""
    n = _normalize(command).lower()
    return any(n.startswith(p.lower()) for p in BLOCKED_PREFIXES)


# ── Allow-list matching ────────────────────────────────────────────────────────

# Allow-list entries follow the pattern:  Bash(<prefix>*)
# where the trailing ``*`` means "this prefix and anything after it".
_SESSION_ALLOW_RULES: list[str] = []


def _parse_allow_rule_prefix(rule: str) -> str | None:
    """
    Extract the command prefix from an allow-rule like ``Bash(git commit*)``

    Returns None for non-Bash rules so they are silently ignored here.
    """
    m = re.match(r"^Bash\((.+?)\*?\)$", rule.strip())
    return m.group(1) if m else None


def is_allowed_by_rules(command: str, allow_rules: list[str]) -> bool:
    """Return True when *command* is covered by at least one allow rule."""
    n = _normalize(command)
    for rule in allow_rules:
        prefix = _parse_allow_rule_prefix(rule)
        if prefix is None:
            continue
        if n == prefix.rstrip() or n.startswith(prefix):
            return True
    return False


def add_session_allow_rules(rules: list[str]) -> None:
    """Extend the session-scoped allow-list with *rules*."""
    _SESSION_ALLOW_RULES.extend(rules)


def clear_session_allow_rules() -> None:
    """Remove all session-scoped allow rules."""
    _SESSION_ALLOW_RULES.clear()


# ── Docker sandbox configuration ──────────────────────────────────────────────


def is_docker_sandbox_enabled() -> bool:
    """Return True when the Docker sandbox is activated via env var."""
    return os.environ.get("AGENT_BUTLER_DOCKER_SANDBOX", "").lower() in ("1", "true", "yes")


def build_docker_command(
    inner_command: str,
    *,
    image: str | None = None,
    workspace_dir: str | None = None,
    network: str = "none",
    read_only_root: bool = True,
) -> list[str]:
    """
    Wrap *inner_command* in a Docker run invocation.

    The workspace directory is mounted read-write at ``/workspace``.
    The container root filesystem is optionally read-only.
    Network access is disabled by default.
    """
    image = image or os.environ.get("AGENT_BUTLER_DOCKER_IMAGE", "agent-butler-sandbox:latest")
    workspace_dir = workspace_dir or os.getcwd()

    cmd: list[str] = [
        "docker", "run",
        "--rm",                        # auto-remove container after exit
        "-i",                          # keep stdin open
        f"--network={network}",        # network isolation
        "-v", f"{workspace_dir}:/workspace",
        "-w", "/workspace",
    ]
    if read_only_root:
        cmd.append("--read-only")

    cmd += [image, "/bin/sh", "-c", inner_command]
    return cmd


# ── Permission check ──────────────────────────────────────────────────────────


def check_sandbox_permission(
    command: str,
    *,
    mode: str = "default",
    extra_allow_rules: list[str] | None = None,
) -> dict[str, Any]:
    """
    Classify a Bash command before execution.

    Returns a dict with:
      - behavior: "allow" | "ask" | "deny"
      - reason:   human-readable explanation
      - docker:   True when the command should run inside Docker
    """
    all_allow_rules = [*_SESSION_ALLOW_RULES, *(extra_allow_rules or [])]

    # Auto mode trusts everything.
    if mode == "auto":
        return {"behavior": "allow", "reason": "auto mode", "docker": False}

    # Plan mode blocks all shell writes.
    if mode == "plan" and not is_safe_read_only(command):
        return {
            "behavior": "deny",
            "reason": "plan mode blocks non-read-only shell commands",
            "docker": False,
        }

    # Known-safe read-only commands.
    if is_safe_read_only(command):
        return {"behavior": "allow", "reason": "read-only command", "docker": False}

    # Explicitly blocked.
    if is_blocked(command):
        return {
            "behavior": "deny",
            "reason": "blocked by sandbox policy",
            "docker": False,
        }

    # Session-level allow rules.
    if is_allowed_by_rules(command, all_allow_rules):
        run_in_docker = is_docker_sandbox_enabled()
        return {
            "behavior": "allow",
            "reason": "allowed by session rule",
            "docker": run_in_docker,
        }

    # Default: ask the user.
    return {
        "behavior": "ask",
        "reason": "command may modify local state",
        "docker": is_docker_sandbox_enabled(),
    }


# ── BashSandbox tool ───────────────────────────────────────────────────────────


class BashSandboxTool:
    """
    Execute a shell command with sandbox policy enforcement.

    When Docker is enabled, approved commands are wrapped in ``docker run``
    before execution.
    """

    name = "Bash"
    description = "Execute a shell command in the workspace."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        import asyncio

        command: str = input.get("command", "")
        cwd: str = context.get("cwd", os.getcwd())
        mode: str = context.get("permission_mode", "default")

        result = check_sandbox_permission(command, mode=mode)
        if result["behavior"] == "deny":
            return {
                "content": f"Blocked: {result['reason']}",
                "is_error": True,
            }

        if result["behavior"] == "ask":
            # In a real UI this would block until the user approves.
            # For teaching purposes we simply deny.
            return {
                "content": "Permission required: user has not approved this command.",
                "is_error": True,
            }

        # Execute the command (optionally inside Docker).
        if result.get("docker"):
            argv = build_docker_command(command, workspace_dir=cwd)
        else:
            argv = [os.environ.get("SHELL", "/bin/sh"), "-lc", command]

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=os.environ.copy(),
        )
        stdout, stderr = await proc.communicate()
        exit_code = proc.returncode or 0

        parts = [f"Exit code: {exit_code}"]
        if stdout:
            parts.extend(["STDOUT:", stdout.decode(errors="replace")])
        if stderr:
            parts.extend(["STDERR:", stderr.decode(errors="replace")])

        return {"content": "\n".join(parts).strip(), "is_error": exit_code != 0}


# ── Singleton ─────────────────────────────────────────────────────────────────

bash_sandbox_tool = BashSandboxTool()
