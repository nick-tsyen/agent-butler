"""
Step 2 - Minimal interactive REPL

Goal:
- show how multi-turn chat works in the terminal
- keep state in memory
- print streaming text incrementally

This version uses Python's asyncio + input() for teaching simplicity.
The real project uses Rich / prompt_toolkit for a richer terminal UI.
"""

import asyncio
import sys
from typing import Any

from .step1 import stream_message


async def _async_input(prompt: str) -> str:
    """Non-blocking input() wrapper that runs in a thread pool executor."""
    loop = asyncio.get_event_loop()
    # Run blocking input() in a thread so the event loop stays free.
    return await loop.run_in_executor(None, input, prompt)


async def run_repl(
    *,
    model: str | None = None,
    system: str | None = None,
) -> None:
    """
    Run an interactive multi-turn chat REPL in the terminal.

    Slash commands:
      /exit  — quit the REPL
      /clear — clear conversation history
    """
    # In-memory message history for the session.
    messages: list[dict[str, Any]] = []

    print("Agent Butler REPL")
    print("Type /exit to quit, /clear to clear history.")

    while True:
        # Read one line from the user (non-blocking via thread executor).
        try:
            raw = await _async_input("> ")
        except (EOFError, KeyboardInterrupt):
            # Graceful exit on Ctrl-D / Ctrl-C.
            print()
            break

        text = raw.strip()
        if not text:
            continue  # skip blank lines

        if text == "/exit":
            break

        if text == "/clear":
            messages.clear()
            print("(history cleared)")
            continue

        # Append the user turn before calling the API.
        messages.append({"role": "user", "content": text})

        # Build kwargs for stream_message — only pass optional args if set.
        stream_kwargs: dict[str, Any] = {"messages": messages}
        if model:
            stream_kwargs["model"] = model
        if system:
            stream_kwargs["system"] = system

        # Get the async generator.
        gen = stream_message(**stream_kwargs)

        # The final assembled result is carried inside the "message_done" event.
        final_result: dict[str, Any] | None = None

        sys.stdout.write("assistant: ")
        sys.stdout.flush()

        # Drain the stream, printing text fragments as they arrive.
        async for event in gen:
            if event["type"] == "text":
                sys.stdout.write(event["text"])
                sys.stdout.flush()
            elif event["type"] == "tool_use_start":
                # Notify the user that a tool is being called.
                sys.stdout.write(f"\n[tool: {event['name']}]\n")
                sys.stdout.flush()
            elif event["type"] == "message_done":
                # The last event carries the fully assembled message + usage.
                final_result = event

        sys.stdout.write("\n\n")
        sys.stdout.flush()

        if final_result:
            # Add the assistant turn to history so context accumulates.
            messages.append(final_result["assistant_message"])
            usage = final_result.get("usage", {})
            print(
                f"(tokens in/out: {usage.get('input_tokens', 0)}/{usage.get('output_tokens', 0)})"
            )
