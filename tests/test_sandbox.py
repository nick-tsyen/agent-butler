from __future__ import annotations

from agent_butler.sandbox.settings import ResolvedSandboxSettings, resolve_sandbox_settings
from agent_butler.sandbox.should_use import contains_excluded_command, matches_excluded_pattern, should_use_sandbox
from agent_butler.sandbox.types import (
    SandboxFilesystemSettings,
    SandboxNetworkSettings,
    SandboxProfile,
    SandboxSettings,
)
from agent_butler.sandbox.wrap import compile_macos_profile, wrap_with_sandbox


class TestSandboxTypes:
    def test_default_sandbox_settings(self) -> None:
        settings = SandboxSettings()
        assert settings.enabled is False
        assert settings.auto_allow_bash_if_sandboxed is True
        assert settings.allow_unsandboxed_commands is True
        assert settings.excluded_commands == []

    def test_sandbox_filesystem_settings(self) -> None:
        fs = SandboxFilesystemSettings(
            allow_write=["/tmp"],
            deny_write=["/etc"],
            allow_read=["/usr"],
        )
        assert "/tmp" in fs.allow_write
        assert "/etc" in fs.deny_write
        assert "/usr" in fs.allow_read

    def test_sandbox_network_settings(self) -> None:
        net = SandboxNetworkSettings(
            allowed_domains=["api.example.com"],
            denied_domains=["evil.com"],
        )
        assert "api.example.com" in net.allowed_domains
        assert "evil.com" in net.denied_domains


class TestSandboxProfile:
    def test_compile_basic_profile(self) -> None:
        profile = SandboxProfile(
            allow_read=["/usr", "/tmp"],
            allow_write=["/tmp/workspace"],
        )
        sbpl = compile_macos_profile(profile)
        assert "(version 1)" in sbpl
        assert "(deny default)" in sbpl
        assert "file-read*" in sbpl
        assert "file-write*" in sbpl
        assert "/tmp/workspace" in sbpl

    def test_compile_with_domains(self) -> None:
        profile = SandboxProfile(allowed_domains=["api.example.com"])
        sbpl = compile_macos_profile(profile)
        assert "network-outbound" in sbpl
        assert "api.example.com" in sbpl

    def test_compile_no_domains_denies_network(self) -> None:
        profile = SandboxProfile()
        sbpl = compile_macos_profile(profile)
        assert "(deny network-outbound)" in sbpl

    def test_wrap_with_sandbox(self) -> None:
        profile = SandboxProfile(allow_read=["/tmp"])
        result = wrap_with_sandbox("echo hello", profile)
        assert "sandbox-exec" in result["wrapped_command"]
        assert "echo hello" in result["wrapped_command"]
        assert "profile" in result


class TestShouldUse:
    def test_disabled_settings(self) -> None:
        settings = ResolvedSandboxSettings(enabled=False)
        assert should_use_sandbox({"command": "echo hi"}, settings) is False

    def test_empty_command(self) -> None:
        settings = ResolvedSandboxSettings(enabled=True)
        assert should_use_sandbox({"command": ""}, settings) is False
        assert should_use_sandbox({"command": "  "}, settings) is False

    def test_dangerously_disable_sandbox(self) -> None:
        settings = ResolvedSandboxSettings(enabled=True, allow_unsandboxed_commands=True)
        assert should_use_sandbox(
            {"command": "echo hi", "dangerouslyDisableSandbox": True},
            settings,
        ) is False

    def test_excluded_command(self) -> None:
        settings = ResolvedSandboxSettings(enabled=True, excluded_commands=["docker"])
        assert should_use_sandbox({"command": "docker build ."}, settings) is False

    def test_normal_command_uses_sandbox(self) -> None:
        settings = ResolvedSandboxSettings(enabled=True)
        assert should_use_sandbox({"command": "echo hi"}, settings) is True


class TestMatchesExcludedPattern:
    def test_exact_match(self) -> None:
        assert matches_excluded_pattern("docker", "docker") is True

    def test_prefix_wildcard(self) -> None:
        assert matches_excluded_pattern("docker build", "docker:*") is True

    def test_glob_match(self) -> None:
        assert matches_excluded_pattern("test-file.txt", "*.txt") is True

    def test_no_match(self) -> None:
        assert matches_excluded_pattern("npm install", "docker") is False

    def test_contains_excluded(self) -> None:
        assert contains_excluded_command("npm install && docker build", ["docker"]) is True


class TestResolveSandboxSettings:
    def test_merge_user_and_project(self) -> None:
        user = SandboxSettings(enabled=True, excluded_commands=["docker"])
        project = SandboxSettings(enabled=False, excluded_commands=["ssh"])
        resolved = resolve_sandbox_settings(user, project)
        assert resolved.enabled is True
        assert "docker" in resolved.excluded_commands
        assert "ssh" in resolved.excluded_commands

    def test_project_overrides_user_enabled(self) -> None:
        user = SandboxSettings(enabled=False)
        project = SandboxSettings(enabled=True)
        resolved = resolve_sandbox_settings(user, project)
        assert resolved.enabled is True
