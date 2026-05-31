from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def mock_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    user_dir = tmp_path / "user_settings"
    user_dir.mkdir()
    user_settings = user_dir / "settings.json"
    user_settings.write_text(json.dumps({
        "allow": [],
        "deny": [],
    }))

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_settings = project_dir / ".agent-butler"
    project_settings.mkdir()
    (project_settings / "settings.json").write_text(json.dumps({
        "allow": [],
        "deny": [],
    }))

    monkeypatch.setattr(
        "agent_butler.utils.paths.get_user_settings_path",
        lambda: str(user_settings),
    )
    monkeypatch.setattr(
        "agent_butler.utils.paths.get_project_settings_path",
        lambda cwd: str(project_settings / "settings.json"),
    )
    monkeypatch.setattr(
        "agent_butler.utils.paths.get_settings_paths",
        lambda cwd: {
            "user": str(user_settings),
            "project": str(project_settings / "settings.json"),
        },
    )

    return {
        "user_dir": str(user_dir),
        "project_dir": str(project_dir),
        "user_settings": str(user_settings),
        "project_settings": str(project_settings / "settings.json"),
    }


@pytest.fixture
def mock_anthropic(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_client = MagicMock()
    mock_messages = MagicMock()
    mock_client.messages = mock_messages

    monkeypatch.setattr(
        "agent_butler.services.api.client.get_anthropic_client",
        lambda **kwargs: mock_client,
    )
    return mock_client
