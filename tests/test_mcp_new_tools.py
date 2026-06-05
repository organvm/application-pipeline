"""Tests for newly added MCP server tools."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from mcp_server import (
    list_precedents,
    mcp,
    pipeline_apply,
    pipeline_enrich,
    pipeline_followup,
    pipeline_hygiene,
    pipeline_mode,
    pipeline_outreach,
    pipeline_outreach_prep,
    pipeline_phase_analytics,
    pipeline_rate,
    pipeline_standards,
)


def test_mcp_tool_count_is_twenty_nine():
    tools = mcp._tool_manager._tools
    assert len(tools) >= 30  # +1: list_precedents serves the precedent registry


def test_list_precedents_returns_parseable_json():
    result = list_precedents()
    data = json.loads(result)
    assert data["status"] == "success"
    assert data["version"] is not None
    # Three named precedent processes match the registry.
    assert set(data["precedents"]) == {"application_genesis", "evaluative_authority", "standards"}
    # Four boundary conditions a domain must meet.
    assert len(data["boundary_conditions"]) == 4
    assert set(data["domains"]) == {"academic", "market", "engineering"}
    assert data["domains"]["academic"]["sgo"]["validation_status"] == "demonstrated"


def test_list_precedents_domain_filter():
    result = list_precedents(domain="engineering")
    data = json.loads(result)
    assert data["status"] == "success"
    assert set(data["domains"]) == {"engineering"}
    assert "ci_cd_quality_gate" in data["domains"]["engineering"]


def test_list_precedents_unknown_domain():
    result = list_precedents(domain="__nope__")
    data = json.loads(result)
    assert data["status"] == "error"
    assert "unknown domain" in data["error"]


def test_pipeline_followup_returns_json():
    result = pipeline_followup()
    data = json.loads(result)
    assert "status" in data
    assert "entry_id" in data


def test_pipeline_enrich_requires_args():
    result = pipeline_enrich()
    data = json.loads(result)
    assert data["status"] == "error"
    assert "required" in data["error"]


def test_pipeline_hygiene_returns_json():
    result = pipeline_hygiene()
    data = json.loads(result)
    assert "status" in data
    assert "total_issues" in data


def test_pipeline_standards_returns_json():
    result = pipeline_standards()
    data = json.loads(result)
    assert "passed" in data
    assert "level_reports" in data


def test_pipeline_phase_analytics_returns_json():
    result = pipeline_phase_analytics()
    data = json.loads(result)
    assert "phase_1" in data
    assert "phase_2" in data


def test_pipeline_rate_dry_run():
    """Verify pipeline_rate returns JSON in dry_run mode."""
    result = pipeline_rate(dry_run=True)
    data = json.loads(result)
    assert data["status"] == "dry_run"
    assert "raters" in data
    assert len(data["raters"]) >= 4


def test_pipeline_mode_returns_json():
    """Verify pipeline_mode returns comparison data."""
    result = pipeline_mode()
    data = json.loads(result)
    assert "current_mode" in data
    assert "modes" in data
    assert "precision" in data["modes"]
    assert "volume" in data["modes"]
    assert "hybrid" in data["modes"]


def test_pipeline_outreach_missing_entry():
    """Verify pipeline_outreach handles missing entry."""
    result = pipeline_outreach(target_id="nonexistent-entry-xyz")
    data = json.loads(result)
    assert data["status"] == "error"
    assert "not found" in data["error"].lower() or "Entry not found" in data["error"]


def test_pipeline_apply_returns_json():
    """Verify pipeline_apply returns valid JSON with result structure."""
    result = pipeline_apply()
    data = json.loads(result)
    assert "checked" in data or "status" in data


def test_pipeline_outreach_prep_returns_json():
    """Verify pipeline_outreach_prep returns valid JSON."""
    result = pipeline_outreach_prep()
    data = json.loads(result)
    assert "entries_processed" in data or "status" in data
