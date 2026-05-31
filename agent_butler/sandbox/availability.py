from __future__ import annotations

import platform
import shutil

_cached_supported: bool | None = None
_cached_reason: str | None = None


def is_platform_supported() -> bool:
    return platform.system() == "Darwin"


def get_sandbox_unavailable_reason(enabled_in_settings: bool) -> str | None:
    global _cached_reason
    if _cached_reason is not None:
        return _cached_reason if enabled_in_settings else None

    if not is_platform_supported():
        _cached_reason = f"Sandbox is not supported on {platform.system()}"
    elif not shutil.which("sandbox-exec"):
        _cached_reason = "sandbox-exec binary not found"
    else:
        _cached_reason = None

    return _cached_reason if enabled_in_settings else None


def is_sandbox_runtime_ready() -> bool:
    return is_platform_supported() and shutil.which("sandbox-exec") is not None


def _reset_availability_cache() -> None:
    global _cached_supported, _cached_reason
    _cached_supported = None
    _cached_reason = None
