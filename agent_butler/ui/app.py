from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
from rich.live import Live

from ..permissions.permissions import PermissionMode
from ..state.task_mode_store import get_task_mode, set_task_mode, subscribe_task_mode
from ..state.task_store import list_tasks, subscribe_tasks
from ..state.todo_store import subscribe_todos
from .events import (
    UIAssistantMessage,
    UIError,
    UIPermissionRequest,
    UISystemNotice,
    UITextDelta,
    UIToolDone,
    UIToolResultMessage,
    UIToolStart,
    UITurnComplete,
    UIUsageUpdate,
)
from .input_prompt import InputPrompt
from .layout import TUILayout
from .session_hook import SessionController


class App:
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        cwd: str | None = None,
        permission_mode: PermissionMode | None = None,
        resume_session_id: str | None = None,
    ) -> None:
        self._model = model
        self._cwd = cwd or __import__("os").getcwd()
        self._permission_mode = permission_mode
        self._resume_session_id = resume_session_id
        self._session: SessionController | None = None
        self._running = False
        self._console = Console()
        self._input = InputPrompt()
        self._layout = TUILayout()
        self._live: Live | None = None

    async def run(self) -> None:
        self._session = SessionController(
            model=self._model,
            cwd=self._cwd,
            permission_mode=self._permission_mode,
        )
        await self._session.initialize()

        self._layout.set_model(self._model)
        if self._permission_mode:
            self._layout.set_mode(self._permission_mode)

        self._setup_store_subscriptions()
        self._running = True
        self._print_welcome()

        try:
            while self._running:
                try:
                    user_input = await self._input.get_input(self._build_prompt())
                except (KeyboardInterrupt, EOFError):
                    break

                if not user_input:
                    continue

                stripped = user_input.strip()

                if stripped in ("/exit", "/quit", "/bye"):
                    break

                if stripped.startswith("/"):
                    await self._handle_command(stripped)
                    continue

                if self._session and self._session._permission_resolver:
                    await self._handle_permission_input(stripped)
                    continue

                await self._handle_submit(stripped)

        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._running = False
            if self._session:
                await self._session.interrupt()

    async def _handle_submit(self, text: str) -> None:
        if not self._session:
            return

        self._layout.set_loading(True)
        self._layout.status_bar.set_notice(None)
        self._layout.tool_calls.clear()

        try:
            with Live(
                self._layout.render(),
                console=self._console,
                refresh_per_second=20,
                auto_refresh=False,
                transient=False,
            ) as live:
                self._live = live

                async for event in self._session.submit(text):
                    if isinstance(event, UITextDelta):
                        self._layout.handle_text_delta(event)
                    elif isinstance(event, UIToolStart):
                        self._layout.handle_tool_start(event)
                    elif isinstance(event, UIToolDone):
                        self._layout.handle_tool_done(event)
                    elif isinstance(event, UIPermissionRequest):
                        self._layout.handle_permission_request(event)
                        self._layout.set_loading(True, "Waiting for permission")
                        self._refresh()
                        decision = await self._wait_for_permission_input()
                        self._session.resolve_permission(decision)
                        self._layout.status_bar.set_permission_prompt(None)
                    elif isinstance(event, UIAssistantMessage):
                        self._layout.finalize_message()
                        self._layout.conversation.set_messages(
                            self._session.state.messages
                        )
                    elif isinstance(event, UIToolResultMessage):
                        self._layout.tool_calls.clear()
                        self._layout.conversation.set_messages(
                            self._session.state.messages
                        )
                    elif isinstance(event, UIUsageUpdate):
                        self._layout.handle_usage_update(event)
                    elif isinstance(event, UISystemNotice):
                        self._layout.handle_system_notice(event)
                    elif isinstance(event, UIError):
                        self._layout.status_bar.set_notice(
                            {"tone": "error", "title": "Error", "body": event.message}
                        )
                    elif isinstance(event, UITurnComplete):
                        pass

                    self._refresh()

        except Exception as exc:
            self._layout.status_bar.set_notice(
                {"tone": "error", "title": "Error", "body": str(exc)}
            )
        finally:
            self._layout.set_loading(False)
            self._layout.flush_stream()
            self._live = None
            self._console.print(self._layout.render())

    async def _wait_for_permission_input(self) -> str:
        self._live = None
        self._console.print(self._layout.render())
        while True:
            try:
                user_input = await self._input.get_input("Decision (y/n/a): ")
            except (KeyboardInterrupt, EOFError):
                return "deny"

            decision_input = user_input.strip().lower()
            if decision_input == "y":
                return "allow_once"
            elif decision_input == "a":
                return "allow_always"
            elif decision_input == "n":
                return "deny"

    async def _handle_permission_input(self, text: str) -> None:
        if not self._session:
            return
        decision_input = text.strip().lower()
        if decision_input == "y":
            self._session.resolve_permission("allow_once")
        elif decision_input == "a":
            self._session.resolve_permission("allow_always")
        else:
            self._session.resolve_permission("deny")

    async def _handle_command(self, cmd: str) -> None:
        if not self._session:
            return

        if cmd == "/help":
            self._console.print(
                "[bold]Commands:[/bold]\n"
                "  /help     Show available commands\n"
                "  /clear    Clear conversation history\n"
                "  /cost     Show session token usage\n"
                "  /model    Inspect or override the session model\n"
                "  /mode     Inspect or switch permission mode\n"
                "  /tasks    Switch task system\n"
                "  /compact  Compact conversation context\n"
                "  /skills   List loaded skills\n"
                "  /agents   List agent definitions\n"
                "  /mcp      Inspect MCP servers\n"
                "  /exit     Exit session"
            )

        elif cmd == "/clear":
            self._session.clear_context()
            self._layout.clear_conversation()
            self._console.print("[dim]Conversation cleared.[/dim]")

        elif cmd == "/cost":
            usage = self._session.state.total_usage
            self._console.print(
                f"[dim]Total tokens: {usage.input_tokens:,} in / "
                f"{usage.output_tokens:,} out[/dim]"
            )

        elif cmd.startswith("/model"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                new_model = parts[1].strip()
                self._session._model = new_model
                self._layout.set_model(new_model)
                self._console.print(f"[dim]Model set to {new_model}[/dim]")
            else:
                self._console.print(
                    f"[dim]Current model: {self._session.model}[/dim]"
                )

        elif cmd.startswith("/mode"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                new_mode = parts[1].strip()
                if new_mode in ("default", "plan", "auto"):
                    self._session.state.permission_mode = new_mode
                    self._layout.set_mode(new_mode)
                    self._console.print(
                        f"[dim]Permission mode set to {new_mode}[/dim]"
                    )
                else:
                    self._console.print(
                        f"[red]Unknown mode: {new_mode}. "
                        "Use default, plan, or auto.[/red]"
                    )
            else:
                self._console.print(
                    f"[dim]Current mode: "
                    f"{self._session.state.permission_mode}[/dim]"
                )

        elif cmd.startswith("/tasks"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                task_mode = parts[1].strip()
                set_task_mode(task_mode)
                self._console.print(
                    f"[dim]Task mode set to {task_mode}[/dim]"
                )
            else:
                current = get_task_mode()
                self._console.print(
                    f"[dim]Current task mode: {current}[/dim]"
                )

        elif cmd == "/compact":
            self._console.print(
                "[dim]Compaction not yet implemented.[/dim]"
            )

        elif cmd == "/skills":
            from ..services.skills.registry import get_all_skills

            skills = get_all_skills()
            if skills:
                self._console.print(f"[bold]Skills ({len(skills)}):[/bold]")
                for s in skills:
                    self._console.print(f"  {s.name} — {s.description}")
            else:
                self._console.print("[dim]No skills loaded.[/dim]")

        elif cmd == "/agents":
            from ..agents.registry import get_all_agents

            agents = get_all_agents()
            if agents:
                self._console.print(f"[bold]Agents ({len(agents)}):[/bold]")
                for a in agents:
                    self._console.print(f"  {a.agent_type} — {a.description}")
            else:
                self._console.print("[dim]No agents registered.[/dim]")

        elif cmd == "/mcp":
            from ..services.mcp.registry import get_all_mcp_tools

            tools = get_all_mcp_tools()
            if tools:
                self._console.print(f"[bold]MCP Tools ({len(tools)}):[/bold]")
                for t in tools:
                    self._console.print(f"  {t.name}")
            else:
                self._console.print("[dim]No MCP tools connected.[/dim]")

        else:
            self._console.print(f"[red]Unknown command: {cmd}[/red]")

    def _setup_store_subscriptions(self) -> None:
        subscribe_todos(self._on_todos_changed)
        subscribe_tasks(self._on_tasks_changed)
        subscribe_task_mode(self._on_task_mode_changed)

    def _on_todos_changed(
        self, session_id: str, todos: list[dict[str, Any]]
    ) -> None:
        self._layout.todo_list.set_todos(todos)
        self._refresh()

    def _on_tasks_changed(self, list_id: str) -> None:
        asyncio.get_event_loop().create_task(self._refresh_tasks(list_id))

    async def _refresh_tasks(self, list_id: str) -> None:
        tasks = await list_tasks(list_id)
        self._layout.task_list.set_tasks(tasks)
        self._refresh()

    def _on_task_mode_changed(self, mode: str) -> None:
        self._layout.set_mode(mode)
        self._refresh()

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._layout.render(), refresh=True)

    def _print_welcome(self) -> None:
        self._console.print("[bold]Agent Butler[/bold] v0.1.0")
        self._console.print(f"[dim]Model: {self._model}[/dim]")
        self._console.print(f"[dim]Working directory: {self._cwd}[/dim]")
        self._console.print(
            "[dim]Type /help for commands, /exit to quit.[/dim]\n"
        )

    def _build_prompt(self) -> str:
        mode = ""
        if self._session:
            mode = self._session.state.permission_mode
        if mode and mode != "default":
            return f"[{mode}] > "
        return "> "
