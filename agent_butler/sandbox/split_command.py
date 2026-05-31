from __future__ import annotations

import shlex


def split_command(command: str) -> list[str]:
    operators = {"&&", "||", ";", "|", "&"}
    segments: list[str] = []
    current = ""
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            current += ch
        elif ch == '"' and not in_single:
            in_double = not in_double
            current += ch
        elif not in_single and not in_double:
            if ch in ("&", "|", ";"):
                op = ch
                if i + 1 < len(command) and command[i + 1] == ch and ch in ("&", "|"):
                    op = ch * 2
                    i += 1
                if current.strip():
                    segments.append(current.strip())
                current = ""
            else:
                current += ch
        else:
            current += ch
        i += 1
    if current.strip():
        segments.append(current.strip())
    return segments
