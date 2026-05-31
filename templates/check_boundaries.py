#!/usr/bin/env python3
"""Sample architectural-boundary check.

Turns an architectural constraint from CONSTRAINTS.md into an executable gate: scan a directory for
a forbidden pattern and fail the build (exit 1) on any violation, printing an agent-oriented
WHAT / WHY / FIX message so the failure doubles as a repair instruction.

Adapt FORBIDDEN_PATTERN / DIRECTORY / the WHY+FIX text to each constraint you need to enforce, then
wire this into CI and your `make check` / verification path. Add one check function per constraint.
"""

import os
import sys

# --- Configure per constraint -------------------------------------------------
DIRECTORY = "src/renderer"
FORBIDDEN_PATTERN = "import fs from"
SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
WHY = "The renderer layer must remain decoupled from OS operations (security and portability)."
FIX = "Move file logic to src/preload/file-ops.ts and invoke it via window.api."
# -----------------------------------------------------------------------------


def check_architectural_boundary(directory: str = DIRECTORY) -> None:
    violations: list[tuple[str, int]] = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(SOURCE_EXTENSIONS):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, start=1):
                        if FORBIDDEN_PATTERN in line:
                            violations.append((file_path, line_num))

    if violations:
        for path, line in violations:
            print(f"ERROR: Forbidden pattern '{FORBIDDEN_PATTERN}' in {path}:{line}")
            print(f"WHY: {WHY}")
            print(f"FIX: {FIX}")
        sys.exit(1)

    print(f"Architecture check passed: no '{FORBIDDEN_PATTERN}' in {directory}.")


if __name__ == "__main__":
    check_architectural_boundary()
