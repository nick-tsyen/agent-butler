"""
Step 20 - Background agents with Git worktrees

Goal:
- run agents on independent tasks in parallel using Git worktrees
- isolate each task in its own filesystem branch so changes don't collide
- wire up background asyncio tasks + optional process isolation
- provide a minimal "agent farm" that spawns N workers and collects results

This is the most advanced step — it combines worktrees, subprocesses,
asyncio concurrency, and the agentic loop from step 4.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

# ── Worktree helpers ───────────────────────────────────────────────────────────


def _git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a git command synchronously and return the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _get_repo_root(cwd: str) -> str:
    """Return the absolute path of the Git repo root that contains *cwd*."""
    result = _git("rev-parse", "--show-toplevel", cwd=cwd)
    return result.stdout.strip()


def _get_current_branch(cwd: str) -> str:
    """Return the current branch name."""
    result = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    return result.stdout.strip()


def create_worktree(
    *, repo_root: str, branch_name: str, worktree_path: str
) -> dict[str, Any]:
    """
    Create a Git worktree at *worktree_path* on a new branch *branch_name*.

    The new branch is created from the current HEAD.  The worktree directory
    must not already exist.
    """
    _git("worktree", "add", "-b", branch_name, worktree_path, cwd=repo_root)
    return {
        "branch": branch_name,
        "path": worktree_path,
        "repo_root": repo_root,
    }


def remove_worktree(*, repo_root: str, worktree_path: str, force: bool = True) -> None:
    """Remove a Git worktree and its associated branch."""
    branch_name: str | None = None
    try:
        result = _git("branch", "--show-current", cwd=worktree_path)
        branch_name = result.stdout.strip() or None
    except subprocess.CalledProcessError:
        pass

    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(worktree_path)

    try:
        _git(*args, cwd=repo_root)
    except subprocess.CalledProcessError:
        shutil.rmtree(worktree_path, ignore_errors=True)

    if branch_name:
        try:
            _git("branch", "-D", branch_name, cwd=repo_root)
        except subprocess.CalledProcessError:
            pass


def list_worktrees(repo_root: str) -> list[dict[str, str]]:
    """Return all worktrees for the repo as a list of dicts."""
    result = _git("worktree", "list", "--porcelain", cwd=repo_root)
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line[len("worktree "):].strip()
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip().removeprefix("refs/heads/")
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
    if current:
        worktrees.append(current)
    return worktrees


# ── Background agent worker ────────────────────────────────────────────────────


async def run_agent_in_worktree(
    *,
    task_prompt: str,
    repo_root: str,
    worktrees_base: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Spin up a background agent in an isolated Git worktree.

    Workflow:
    1. Create a temporary worktree on a fresh branch.
    2. Run the agentic loop inside that directory.
    3. Return the result and clean up the worktree.

    The worktree is always cleaned up regardless of success or failure.
    """
    # Generate stable identifiers for this background task.
    tid = task_id or uuid.uuid4().hex[:8]
    branch_name = f"agent/{tid}"
    worktree_path = str(Path(worktrees_base) / tid)

    worktree_info = create_worktree(
        repo_root=repo_root,
        branch_name=branch_name,
        worktree_path=worktree_path,
    )

    try:
        # Import here to avoid circular imports in the teaching module chain.
        from .step4 import query

        tool_context = {"cwd": worktree_path, "session_id": tid}

        final_result: dict[str, Any] | None = None
        turn_count = 0
        total_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}

        gen = query(
            messages=[{"role": "user", "content": task_prompt}],
            tool_context=tool_context,
            max_turns=20,
        )

        async for event in await gen:
            if event.get("type") in ("assistant_message", "tool_result_message"):
                turn_count += 1
            elif event.get("type") == "query_done":
                # The query_done event carries the final state and usage.
                final_result = event

        if final_result:
            u = final_result.get("usage", {})
            total_usage["input_tokens"] += u.get("input_tokens", 0)
            total_usage["output_tokens"] += u.get("output_tokens", 0)

        # Extract the last assistant text from the conversation.
        last_text = ""
        if final_result and final_result.get("state", {}).get("messages"):
            messages = final_result["state"]["messages"]
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", [])
                    texts = [b.get("text", "") for b in content if b.get("type") == "text"]
                    last_text = " ".join(texts)
                    break

        return {
            "task_id": tid,
            "branch": branch_name,
            "worktree": worktree_path,
            "status": "completed",
            "result": last_text,
            "turn_count": turn_count,
            "usage": total_usage,
        }

    except Exception as exc:
        return {
            "task_id": tid,
            "branch": branch_name,
            "worktree": worktree_path,
            "status": "error",
            "error": str(exc),
            "result": "",
            "turn_count": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }

    finally:
        # Always remove the worktree so we don't leave stale branches behind.
        remove_worktree(repo_root=repo_root, worktree_path=worktree_path)


# ── Agent farm ────────────────────────────────────────────────────────────────


async def run_parallel_agents(
    tasks: list[str],
    *,
    cwd: str | None = None,
    worktrees_base: str | None = None,
    max_concurrent: int = 4,
) -> list[dict[str, Any]]:
    """
    Run *tasks* as parallel background agents, each in its own worktree.

    Args:
        tasks:          List of task prompt strings.
        cwd:            The working directory (must be inside a Git repo).
        worktrees_base: Directory where worktrees are created.
                        Defaults to a ``../.agent-worktrees`` sibling.
        max_concurrent: Maximum number of agents running at the same time.

    Returns a list of result dicts in the same order as *tasks*.
    """
    effective_cwd = cwd or os.getcwd()
    repo_root = _get_repo_root(effective_cwd)

    if worktrees_base is None:
        # Default: create worktrees as a sibling directory of the repo root.
        worktrees_base = str(Path(repo_root).parent / ".agent-worktrees")
    Path(worktrees_base).mkdir(parents=True, exist_ok=True)

    # Semaphore limits concurrency to avoid overloading the API.
    sem = asyncio.Semaphore(max_concurrent)

    async def _bounded(prompt: str, idx: int) -> dict[str, Any]:
        async with sem:
            return await run_agent_in_worktree(
                task_prompt=prompt,
                repo_root=repo_root,
                worktrees_base=worktrees_base,
                task_id=uuid.uuid4().hex[:8],
            )

    # Kick off all tasks concurrently.
    coros = [_bounded(t, i) for i, t in enumerate(tasks)]
    results = await asyncio.gather(*coros, return_exceptions=True)

    out = []
    for r in results:
        if isinstance(r, BaseException):
            out.append({"status": "error", "error": str(r), "result": ""})
        else:
            out.append(r)

    return out


# ── BackgroundAgent tool ───────────────────────────────────────────────────────


class BackgroundAgentTool:
    """
    Spawn a background agent in a Git worktree to complete a task in parallel.

    The parent agent continues while the background agent works.
    Results are collected later via the results of the gather call.
    """

    name = "BackgroundAgent"
    description = (
        "Spawn a background agent in an isolated Git worktree. "
        "Use for tasks that can proceed independently in parallel."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Full task description for the background agent.",
            },
            "branch_prefix": {
                "type": "string",
                "description": "Optional prefix for the Git branch name.",
            },
        },
        "required": ["prompt"],
    }

    def is_read_only(self) -> bool:
        return False

    def is_enabled(self) -> bool:
        return True

    async def call(
        self, input: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = input.get("prompt", "")
        if not prompt:
            return {"content": "Error: prompt is required", "is_error": True}

        cwd = context.get("cwd", os.getcwd())

        try:
            repo_root = _get_repo_root(cwd)
        except subprocess.CalledProcessError:
            return {
                "content": "Error: current directory is not inside a Git repository.",
                "is_error": True,
            }

        worktrees_base = str(Path(repo_root).parent / ".agent-worktrees")
        task_id = uuid.uuid4().hex[:8]

        # Fire-and-forget: schedule the work but don't await it here.
        # In a real application you'd track the asyncio.Task and surface
        # its result through a separate polling mechanism.
        loop = asyncio.get_event_loop()
        bg_task = loop.create_task(
            run_agent_in_worktree(
                task_prompt=prompt,
                repo_root=repo_root,
                worktrees_base=worktrees_base,
                task_id=task_id,
            )
        )

        # Attach a callback to log errors so the fire-and-forget doesn't
        # silently swallow exceptions.
        def _log_done(future: asyncio.Future) -> None:
            exc = future.exception()
            if exc:
                print(f"[BackgroundAgent/{task_id}] error: {exc}")

        bg_task.add_done_callback(_log_done)

        return {
            "content": "\n".join([
                f"Background agent started (id={task_id}).",
                f"Working in: {worktrees_base}/{task_id}",
                f"Branch: agent/{task_id}",
                "The agent will clean up its worktree when done.",
            ])
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

background_agent_tool = BackgroundAgentTool()
