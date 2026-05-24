"""Global test configuration."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import mkdtemp

# Keep metrics-dependent tests deterministic across developer machines and CI.
os.environ.setdefault("PIPELINE_METRICS_SOURCE", "fallback")

# Prevent test runs from mutating repo-tracked signal action logs.
_TEST_SIGNAL_DIR = Path(mkdtemp(prefix="pipeline-signal-actions-"))
os.environ.setdefault("PIPELINE_SIGNAL_ACTIONS_PATH", str(_TEST_SIGNAL_DIR / "signal-actions.yaml"))

# Prevent the suite from mutating the real pipeline/ tree. Several tests invoke
# standup/morning/campaign (which auto-flush stale job entries and auto-expire
# submissions) against the repo; this guard short-circuits those destructive
# moves. Tests that exercise flush/expire behavior do so on tmp dirs and clear
# this var locally (see tests/test_pipeline_freshness.py). [#57]
os.environ.setdefault("PIPELINE_NO_MUTATE", "1")
