from __future__ import annotations

import shlex

from .types import SandboxProfile


def _shell_quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _escape_sbpl_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _subpath(p: str) -> str:
    return f'(subpath "{_escape_sbpl_string(p)}")'


def compile_macos_profile(profile: SandboxProfile) -> str:
    lines = [
        "(version 1)",
        "(deny default)",
        "(allow process-exec)",
        "(allow process-fork)",
        "(allow signal)",
        "(allow mach-lookup)",
        "(allow ipc-posix-shm-read-data)",
        "(allow ipc-posix-shm-write-data)",
        "(allow sysctl-read)",
        "(allow file-read-metadata)",
    ]

    for p in profile.allow_read:
        lines.append(f"(allow file-read* {_subpath(p)})")

    for p in profile.allow_write:
        lines.append(f"(allow file-write* {_subpath(p)})")

    for p in profile.deny_write:
        lines.append(f"(deny file-write* {_subpath(p)})")

    if profile.allowed_domains:
        lines.append("(allow network-outbound)")
        for domain in profile.allowed_domains:
            lines.append(f'(allow network-outbound (remote ip "{_escape_sbpl_string(domain)}"))')
    else:
        lines.append("(deny network-outbound)")

    return "\n".join(lines)


def wrap_with_sandbox(command: str, profile: SandboxProfile) -> dict[str, str]:
    sbpl = compile_macos_profile(profile)
    quoted_profile = _shell_quote_single(sbpl)
    quoted_command = _shell_quote_single(command)
    wrapped = f"/usr/bin/sandbox-exec -p {quoted_profile} /bin/bash -lc {quoted_command}"
    return {"wrapped_command": wrapped, "profile": sbpl}
