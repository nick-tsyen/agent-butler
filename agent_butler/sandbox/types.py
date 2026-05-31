from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class SandboxFilesystemSettings:
    allow_write: list[str] = field(default_factory=list)
    deny_write: list[str] = field(default_factory=list)
    allow_read: list[str] = field(default_factory=list)
    deny_read: list[str] = field(default_factory=list)


@dataclass
class SandboxNetworkSettings:
    allowed_domains: list[str] = field(default_factory=list)
    denied_domains: list[str] = field(default_factory=list)


@dataclass
class SandboxSettings:
    enabled: bool = False
    auto_allow_bash_if_sandboxed: bool = True
    allow_unsandboxed_commands: bool = True
    excluded_commands: list[str] = field(default_factory=list)
    filesystem: SandboxFilesystemSettings = field(default_factory=SandboxFilesystemSettings)
    network: SandboxNetworkSettings = field(default_factory=SandboxNetworkSettings)


@dataclass
class SandboxProfile:
    allow_write: list[str] = field(default_factory=list)
    deny_write: list[str] = field(default_factory=list)
    allow_read: list[str] = field(default_factory=list)
    deny_read: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    denied_domains: list[str] = field(default_factory=list)
