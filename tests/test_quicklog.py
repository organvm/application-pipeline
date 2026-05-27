import sys
from pathlib import Path

import pytest
import yaml

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_lib
import quicklog


def test_slugify():
    assert quicklog._slugify("Grafana Labs") == "grafana-labs"
    assert quicklog._slugify("Staff AI Engineer") == "staff-ai-engineer"
    assert quicklog._slugify("Test! @#$% Org") == "test-org"

def test_quicklog_creation(tmp_path, monkeypatch):
    # Mock REPO_ROOT and pipeline dirs
    monkeypatch.setattr(quicklog, "REPO_ROOT", tmp_path)
    
    # Create necessary dirs in tmp_path
    submitted_dir = tmp_path / "pipeline" / "submitted"
    submitted_dir.mkdir(parents=True)
    
    # Mock ALL_PIPELINE_DIRS_WITH_POOL to only check our tmp submitted dir
    monkeypatch.setattr(pipeline_lib, "PIPELINE_DIR_SUBMITTED", submitted_dir)
    monkeypatch.setattr(pipeline_lib, "ALL_PIPELINE_DIRS_WITH_POOL", [submitted_dir])
    
    # Mock get_operator_name
    monkeypatch.setattr(pipeline_lib, "get_operator_name", lambda: "test-user")

    # Call main with args
    test_args = [
        "scripts/quicklog.py",
        "--org", "Test Org",
        "--role", "Test Role",
        "--date", "2026-03-26",
        "--url", "https://example.com/job"
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    
    quicklog.main()
    
    # Verify file existence
    expected_path = submitted_dir / "test-org-test-role.yaml"
    assert expected_path.exists()
    
    # Verify content
    with open(expected_path) as f:
        data = yaml.safe_load(f)
        
    assert data["id"] == "test-org-test-role"
    assert data["target"]["organization"] == "Test Org"
    assert data["target"]["url"] == "https://example.com/job"
    assert data["timeline"]["submitted"] == "2026-03-26"
    assert data["status"] == "submitted"
    assert "applied-outside-pipeline" in data["tags"]
    assert data["status_meta"]["submitted_by"] == "test-user"

def test_quicklog_duplicate_error(tmp_path, monkeypatch):
    # Mock REPO_ROOT and pipeline dirs
    monkeypatch.setattr(quicklog, "REPO_ROOT", tmp_path)
    
    submitted_dir = tmp_path / "pipeline" / "submitted"
    submitted_dir.mkdir(parents=True)
    
    # Create a pre-existing file
    existing_file = submitted_dir / "dup-org-dup-role.yaml"
    existing_file.write_text("exists")
    
    monkeypatch.setattr(pipeline_lib, "PIPELINE_DIR_SUBMITTED", submitted_dir)
    monkeypatch.setattr(pipeline_lib, "ALL_PIPELINE_DIRS_WITH_POOL", [submitted_dir])

    test_args = [
        "scripts/quicklog.py",
        "--org", "Dup Org",
        "--role", "Dup Role"
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    
    with pytest.raises(SystemExit) as excinfo:
        quicklog.main()
    
    assert excinfo.value.code == 1
