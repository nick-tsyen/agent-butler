import os
import tempfile
import json
from pathlib import Path
from agent_butler.utils.paths import get_harness_root, is_harness_workspace
from agent_butler.context.system_prompt import build_system_prompt

def test_harness_workspace_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        sub_dir = tmp_path / "src" / "api"
        sub_dir.mkdir(parents=True)
        
        # Initially not a harness workspace
        assert not is_harness_workspace(str(sub_dir))
        assert get_harness_root(str(sub_dir)) is None
        
        # Add CLAUDE.md to simulate harness workspace root
        claude_file = tmp_path / "CLAUDE.md"
        claude_file.write_text("# Project rules")
        
        # Detection should traverse up and find it
        assert is_harness_workspace(str(sub_dir))
        assert Path(get_harness_root(str(sub_dir))) == tmp_path

def test_system_prompt_harness_injection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        # Create context files
        (tmp_path / "CLAUDE.md").write_text("CLAUDE_RULES")
        (tmp_path / "decisions.md").write_text("DECISIONS_LIST")
        (tmp_path / "claude-progress.md").write_text("PROGRESS_STATE")
        
        # Test without READY.md (should show initialization constraint)
        prompt = build_system_prompt(str(tmp_path), "test-model", [], [], [])
        assert "CLAUDE_RULES" in prompt
        assert "DECISIONS_LIST" in prompt
        assert "PROGRESS_STATE" in prompt
        assert "[CRITICAL CONSTRAINT] READY.md was not found" in prompt
        
        # Test with READY.md (should not show constraint)
        (tmp_path / "READY.md").write_text("READY")
        prompt_ready = build_system_prompt(str(tmp_path), "test-model", [], [], [])
        assert "[CRITICAL CONSTRAINT] READY.md was not found" not in prompt_ready
