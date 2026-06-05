"""Tests for scripts/pipeline_market.py."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_market import build_market_intelligence_loader, check_market_intel_freshness


def test_loader_uses_defaults_when_file_missing(tmp_path):
    load_market_intelligence, get_portal_scores, get_strategic_base, _, _ = build_market_intelligence_loader(tmp_path)

    assert load_market_intelligence() == {}
    assert isinstance(get_portal_scores(), dict)
    assert isinstance(get_strategic_base(), dict)
    assert "email" in get_portal_scores()


def test_loader_reads_market_intel_when_present(tmp_path):
    strategy = tmp_path / "strategy"
    strategy.mkdir(parents=True, exist_ok=True)
    payload = {
        "portal_friction_scores": {"custom_portal": 3},
        "track_benchmarks": {"job": {"acceptance_rate": 0.03}},
    }
    (strategy / "market-intelligence-2026.json").write_text(json.dumps(payload))

    load_market_intelligence, get_portal_scores, get_strategic_base, _, _ = build_market_intelligence_loader(tmp_path)

    intel = load_market_intelligence()
    assert intel["portal_friction_scores"]["custom_portal"] == 3
    assert get_portal_scores()["custom_portal"] == 3
    assert get_strategic_base()["job"] == 7


def test_strategic_base_default_academic(tmp_path):
    """Academic shares the grant/fellowship strategic base of 7."""
    _, _, get_strategic_base, _, strategic_base_default = build_market_intelligence_loader(tmp_path)

    assert strategic_base_default["academic"] == 7
    # With no market-intelligence file present, get_strategic_base() returns the defaults.
    assert get_strategic_base()["academic"] == 7


# ---------------------------------------------------------------------------
# check_market_intel_freshness
# ---------------------------------------------------------------------------


def test_freshness_missing_file(tmp_path):
    """Missing market intel file returns fresh=False with warning."""
    result = check_market_intel_freshness(tmp_path)
    assert result["fresh"] is False
    assert result["age_days"] == -1
    assert "not found" in result["warning"]


def test_freshness_fresh_file(tmp_path):
    """Recently created file is reported as fresh."""
    strategy = tmp_path / "strategy"
    strategy.mkdir()
    intel_file = strategy / "market-intelligence-2026.json"
    intel_file.write_text("{}")

    result = check_market_intel_freshness(tmp_path)
    assert result["fresh"] is True
    assert result["age_days"] < 1
    assert result["warning"] is None


def test_freshness_old_file(tmp_path):
    """File older than 90 days returns fresh=False with WARNING."""
    strategy = tmp_path / "strategy"
    strategy.mkdir()
    intel_file = strategy / "market-intelligence-2026.json"
    intel_file.write_text("{}")

    # Set mtime to 100 days ago
    old_mtime = time.time() - (100 * 86400)
    os.utime(intel_file, (old_mtime, old_mtime))

    result = check_market_intel_freshness(tmp_path)
    assert result["fresh"] is False
    assert result["age_days"] > 90
    assert "WARNING" in result["warning"]


def test_freshness_critical_file(tmp_path):
    """File older than 180 days returns fresh=False with CRITICAL."""
    strategy = tmp_path / "strategy"
    strategy.mkdir()
    intel_file = strategy / "market-intelligence-2026.json"
    intel_file.write_text("{}")

    # Set mtime to 200 days ago
    old_mtime = time.time() - (200 * 86400)
    os.utime(intel_file, (old_mtime, old_mtime))

    result = check_market_intel_freshness(tmp_path)
    assert result["fresh"] is False
    assert result["age_days"] > 180
    assert "CRITICAL" in result["warning"]

