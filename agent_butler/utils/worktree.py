from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

WORKTREES_SUBDIR = str(Path(".agent-butler") / "worktrees")


@dataclass
class WorktreeInfo:
    worktree_path: str
    worktree_branch: str
    head_commit: str
    git_root: str


def _flatten_slug(slug: str) -> str:
    return slug.replace("/", "+")


def worktree_branch_name(slug: str) -> str:
    return f"worktree-{_flatten_slug(slug)}"


def worktree_path_for(repo_root: str, slug: str) -> str:
    return str(Path(repo_root) / WORKTREES_SUBDIR / _flatten_slug(slug))


async def _git(args: list[str], cwd: str) -> dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "code": proc.returncode or 0,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except FileNotFoundError:
        return {"code": 127, "stdout": "", "stderr": "git not found"}
    except Exception as e:
        return {"code": 1, "stdout": "", "stderr": str(e)}


async def find_git_root(cwd: str) -> str | None:
    from typing import Any

    current = Path(cwd).resolve()
    for _ in range(64):
        dot_git = current / ".git"
        if dot_git.exists():
            return str(current)
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


async def is_inside_git_repo(cwd: str) -> bool:
    return (await find_git_root(cwd)) is not None


async def create_agent_worktree(slug: str, cwd: str) -> WorktreeInfo:
    git_root = await find_git_root(cwd)
    if not git_root:
        raise RuntimeError(f"Cannot create worktree: {cwd} is not inside a git repository.")

    head = await _git(["rev-parse", "HEAD"], git_root)
    if head["code"] != 0:
        raise RuntimeError(f"Failed to read HEAD in {git_root}: {head['stderr'].strip() or 'git rev-parse HEAD failed'}")
    head_commit = head["stdout"].strip()

    wt_path = worktree_path_for(git_root, slug)
    wt_branch = worktree_branch_name(slug)

    Path(wt_path).parent.mkdir(parents=True, exist_ok=True)

    add = await _git(["worktree", "add", "-B", wt_branch, wt_path, "HEAD"], git_root)
    if add["code"] != 0:
        raise RuntimeError(f"git worktree add failed: {add['stderr'].strip() or 'exit ' + str(add['code'])}")

    return WorktreeInfo(
        worktree_path=wt_path,
        worktree_branch=wt_branch,
        head_commit=head_commit,
        git_root=git_root,
    )


async def has_worktree_changes(worktree_path: str, head_commit: str) -> bool:
    status = await _git(["status", "--porcelain"], worktree_path)
    if status["code"] != 0:
        return True
    if status["stdout"].strip():
        return True

    rev_list = await _git(["rev-list", "--count", f"{head_commit}..HEAD"], worktree_path)
    if rev_list["code"] != 0:
        return True
    try:
        count = int(rev_list["stdout"].strip())
        if count > 0:
            return True
    except ValueError:
        return True

    return False


async def remove_agent_worktree(info: WorktreeInfo) -> dict[str, Any]:
    errors: list[str] = []

    remove = await _git(["worktree", "remove", "--force", info.worktree_path], info.git_root)
    if remove["code"] != 0:
        errors.append(f"worktree remove: {remove['stderr'].strip() or 'exit ' + str(remove['code'])}")

    branch_delete = await _git(["branch", "-D", info.worktree_branch], info.git_root)
    if branch_delete["code"] != 0:
        errors.append(f"branch -D: {branch_delete['stderr'].strip() or 'exit ' + str(branch_delete['code'])}")

    if errors:
        return {"ok": False, "error": "; ".join(errors)}
    return {"ok": True}
