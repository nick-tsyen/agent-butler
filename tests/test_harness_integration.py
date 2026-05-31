import os
import tempfile
from pathlib import Path
from agent_butler.utils.paths import get_harness_root, is_harness_workspace

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
