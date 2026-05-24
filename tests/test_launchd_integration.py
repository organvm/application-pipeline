"""Tests for LaunchAgent integration and automation layer.

These exercise the owner's local automation environment (a project .venv and
launchd plists with machine-specific paths). They are skipped when that
environment isn't present (e.g. in CI) rather than asserting against it — see
issues #57 (test isolation) and #58 (env-coupled tests).
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
LAUNCHD_DIR = REPO_ROOT / ".config" / "launchd"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# Skip env-coupled tests when the project venv isn't present (CI / other machines).
requires_venv = pytest.mark.skipif(
    not VENV_PYTHON.exists(),
    reason="project .venv not present (owner-local automation env; see #58)",
)

# Subprocesses that invoke real pipeline commands must not mutate the repo tree.
_NO_MUTATE_ENV = {**os.environ, "PIPELINE_NO_MUTATE": "1"}


class TestLaunchAgentPaths:
    """Verify LaunchAgents point to correct Python interpreter."""

    @requires_venv
    def test_all_plists_use_venv_python(self):
        """Every plist should reference the project venv, not system Python."""
        plists = list(LAUNCHD_DIR.glob("com.4jp.pipeline.*.plist"))
        assert len(plists) == 9, f"Expected 9 plists, found {len(plists)}"

        for plist in plists:
            content = plist.read_text()
            assert str(REPO_ROOT / ".venv" / "bin") in content, f"{plist.name} missing venv path"
            assert "/opt/anaconda3" not in content, f"{plist.name} still references anaconda"

    def test_launchd_manager_finds_correct_directory(self):
        """Verify launchd_manager.py looks in .config/launchd, not launchd/."""
        # Import after path is set
        import sys

        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from launchd_manager import LAUNCHD_DIR as MANAGED_DIR

        # Should be .config/launchd, not launchd/
        assert ".config" in str(MANAGED_DIR), f"launchd_manager looks in wrong dir: {MANAGED_DIR}"
        assert MANAGED_DIR.exists(), f"LAUNCHD_DIR does not exist: {MANAGED_DIR}"


class TestPythonEnvironment:
    """Verify Python environment is correctly configured."""

    @requires_venv
    def test_venv_has_required_modules(self):
        """Critical modules should be available in venv."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-c", "import ruamel.yaml; import yaml; print('OK')"], capture_output=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0, f"venv missing dependencies: {result.stderr.decode()}"

    @requires_venv
    def test_pipeline_lib_loads_from_venv(self):
        """pipeline_lib should load without errors when invoked as scripts do."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-c", "import sys; sys.path.insert(0, 'scripts'); import pipeline_lib; print('OK')"],
            capture_output=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, f"pipeline_lib load failed: {result.stderr.decode()}"


class TestSystemMetrics:
    """Verify system-metrics.json is valid and parseable."""

    def test_system_metrics_valid_json(self):
        """system-metrics.json should be valid JSON with no merge conflicts."""
        import json

        metrics_path = Path.home() / "Workspace" / "meta-organvm" / "organvm-corpvs-testamentvm" / "system-metrics.json"
        if not metrics_path.exists():
            pytest.skip("system-metrics.json not found")

        content = metrics_path.read_text()

        # Should not contain git merge conflict markers
        assert "<<<<<<" not in content, "system-metrics.json contains unmerged conflict"
        assert ">>>>>>" not in content, "system-metrics.json contains unmerged conflict"
        assert "<<<<<<" not in content, "system-metrics.json contains conflict markers"

        # Should be valid JSON
        data = json.loads(content)
        assert "computed" in data or "generated" in data


class TestMorningRoutine:
    """Verify morning routine scripts work correctly."""

    @requires_venv
    def test_standup_runs_cleanly(self):
        """standup.py should run without errors."""
        result = subprocess.run(
            [str(VENV_PYTHON), "scripts/run.py", "standup"], capture_output=True, cwd=REPO_ROOT,
            timeout=60, env=_NO_MUTATE_ENV,
        )
        assert result.returncode == 0, f"standup failed: {result.stderr.decode()[:500]}"

    @requires_venv
    def test_morning_runs_cleanly(self):
        """morning.py should run without errors."""
        result = subprocess.run(
            [str(VENV_PYTHON), "scripts/run.py", "morning"], capture_output=True, cwd=REPO_ROOT,
            timeout=60, env=_NO_MUTATE_ENV,
        )
        # May have warnings but should not crash
        assert "Traceback" not in result.stderr.decode(), f"morning crashed: {result.stderr.decode()[:500]}"
