import os
import tempfile
import json
from pathlib import Path
import pytest
from agent_butler.state.task_store import create_task, update_task, list_tasks, get_task
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


@pytest.mark.asyncio
async def test_task_store_feature_list_redirection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        feature_list_file = tmp_path / "feature_list.json"
        feature_list_file.write_text(json.dumps({
            "project": "test-project",
            "features": [
                {
                    "id": "f1",
                    "title": "First feature",
                    "behavior": "First behavior",
                    "status": "not_started"
                },
                {
                    "id": "f2",
                    "title": "Second feature",
                    "behavior": "Second behavior",
                    "status": "in_progress"
                }
            ]
        }))
        
        # Change cwd to tmpdir to trigger harness mode redirection
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # list_tasks
            tasks = await list_tasks("session-1")
            assert len(tasks) == 2
            assert tasks[0]["id"] == "f1"
            assert tasks[0]["status"] == "pending"
            assert tasks[1]["status"] == "in_progress"
            
            # get_task
            task_f1 = await get_task("session-1", "f1")
            assert task_f1["subject"] == "First feature"
            
            # WIP=1 Constraint check: setting f1 to in_progress should raise error
            with pytest.raises(ValueError, match="WIP=1 constraint is active"):
                await update_task("session-1", "f1", {"status": "in_progress"})
                
            # Finish f2 first
            await update_task("session-1", "f2", {"status": "completed"})
            
            # Now f1 can be set to in_progress
            ok = await update_task("session-1", "f1", {"status": "in_progress"})
            assert ok
            
            # Verify file updated
            updated_data = json.loads(feature_list_file.read_text())
            assert updated_data["features"][0]["status"] == "in_progress"
            assert updated_data["features"][1]["status"] == "passing"
        finally:
            os.chdir(orig_cwd)
