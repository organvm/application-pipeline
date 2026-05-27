"""Direct tests for scripts/handoff_seed.py subprocess wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import handoff_seed


def test_run_returns_stripped_command_output():
    assert handoff_seed.run("echo hello") == "hello"


def test_run_returns_na_on_failure():
    assert handoff_seed.run("exit 1") == "N/A"
