from __future__ import annotations

import argparse
import asyncio
import os
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent-butler",
        description="Agent Butler — An AI-powered coding agent",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        help="Model name (default: claude-sonnet-4-20250514 or $ANTHROPIC_MODEL)",
    )
    parser.add_argument(
        "--resume",
        nargs="?",
        const=True,
        default=None,
        metavar="SESSION_ID",
        help="Resume a previous session (optionally specify session ID)",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        default=False,
        help="Start in plan mode (read-only tools only)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        default=False,
        help="Start in auto mode (no permission prompts)",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Working directory (default: current directory)",
    )
    parser.add_argument(
        "--print",
        dest="print_mode",
        action="store_true",
        default=False,
        help="Print mode: send a single message and print the response",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Message to send in print mode",
    )
    return parser.parse_args()


def _determine_permission_mode(args: argparse.Namespace) -> str | None:
    if args.plan:
        return "plan"
    if args.auto:
        return "auto"
    return None


async def _async_main(args: argparse.Namespace) -> None:
    cwd = args.cwd or os.getcwd()
    os.chdir(cwd)

    permission_mode = _determine_permission_mode(args)

    from .services.skills.bootstrap import bootstrap_skills
    skills_result = await bootstrap_skills(cwd)
    if skills_result.skill_count > 0 or skills_result.conditional_count > 0:
        print(
            f"[agent-butler] Loaded {skills_result.skill_count} skill(s)"
            + (f" ({skills_result.conditional_count} conditional)" if skills_result.conditional_count else ""),
            file=sys.stderr,
        )

    from .services.mcp.bootstrap import bootstrap_mcp
    try:
        mcp_result = await bootstrap_mcp(cwd)
        if mcp_result.tool_count > 0:
            connected = sum(
                1 for c in mcp_result.connections
                if getattr(c, "type", None) == "connected"
            )
            print(
                f"[agent-butler] Connected to {connected} MCP server(s) "
                f"with {mcp_result.tool_count} tool(s)",
                file=sys.stderr,
            )
        if mcp_result.config_errors:
            for err in mcp_result.config_errors:
                print(f"[agent-butler] MCP config warning: {err}", file=sys.stderr)
    except Exception as exc:
        print(f"[agent-butler] MCP bootstrap failed: {exc}", file=sys.stderr)

    from .tools.agent_tool import AgentTool
    from .tools.bash_tool import BashTool
    from .tools.enter_plan_mode_tool import EnterPlanModeTool
    from .tools.exit_plan_mode_tool import ExitPlanModeTool
    from .tools.file_edit_tool import FileEditTool
    from .tools.file_read_tool import FileReadTool
    from .tools.file_write_tool import FileWriteTool
    from .tools.glob_tool import GlobTool
    from .tools.grep_tool import GrepTool
    from .tools.memory_write_tool import MemoryWriteTool
    from .tools.registry import register_builtin_tools
    from .tools.skill_tool import SkillTool
    from .tools.task_create_tool import TaskCreateTool
    from .tools.task_get_tool import TaskGetTool
    from .tools.task_list_tool import TaskListTool
    from .tools.task_update_tool import TaskUpdateTool
    from .tools.todo_write_tool import TodoWriteTool

    builtin_tools = [
        BashTool(),
        FileReadTool(),
        FileWriteTool(),
        FileEditTool(),
        GlobTool(),
        GrepTool(),
        SkillTool(),
        TodoWriteTool(),
        TaskCreateTool(),
        TaskUpdateTool(),
        TaskGetTool(),
        TaskListTool(),
        EnterPlanModeTool(),
        ExitPlanModeTool(),
        MemoryWriteTool(),
        AgentTool(),
    ]
    register_builtin_tools(builtin_tools)

    if args.print_mode:
        message = " ".join(args.message) if args.message else ""
        if not message:
            print("[agent-butler] --print mode requires a message", file=sys.stderr)
            sys.exit(1)
        await _run_print_mode(args.model, cwd, permission_mode, message)
    else:
        from .ui.app import App
        app = App(
            model=args.model,
            cwd=cwd,
            permission_mode=permission_mode,
            resume_session_id=args.resume if isinstance(args.resume, str) else None,
        )
        await app.run()

    from .services.mcp.client import disconnect_all
    await disconnect_all()


async def _run_print_mode(
    model: str,
    cwd: str,
    permission_mode: str | None,
    message: str,
) -> None:
    from .ui.events import UIAssistantMessage, UIError, UIPermissionRequest, UITextDelta
    from .ui.session_hook import SessionController

    session = SessionController(
        model=model,
        cwd=cwd,
        permission_mode=permission_mode,
    )
    await session.initialize()


    async for event in session.submit(message):
        if isinstance(event, UITextDelta):
            print(event.text, end="", flush=True)
        elif isinstance(event, UIAssistantMessage):
            pass
        elif isinstance(event, UIPermissionRequest):
            print(f"\nPermission required for {event.tool_name}: {event.summary}", file=sys.stderr)
            print(f"Risk: {event.risk}", file=sys.stderr)
            decision = input("Allow (y/n/a)? ").strip().lower()
            if decision == "y":
                session.resolve_permission("allow_once")
            elif decision == "a":
                session.resolve_permission("allow_always")
            else:
                session.resolve_permission("deny")
        elif isinstance(event, UIError):
            print(f"\nError: {event.message}", file=sys.stderr)

    print()

    usage = session.state.total_usage
    if usage.input_tokens or usage.output_tokens:
        print(
            f"\n[{usage.input_tokens:,} in / {usage.output_tokens:,} out]",
            file=sys.stderr,
        )


def main() -> None:
    from .utils.load_env import load_env
    load_env()

    args = _parse_args()
    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        print("\nGoodbye!", file=sys.stderr)
        sys.exit(0)
