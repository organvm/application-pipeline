"""Tests for scripts/pipeline_api.py helper behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_api as api


def test_natural_next_status_known_and_unknown():
    assert api._natural_next_status("research") == "qualified"
    assert api._natural_next_status("unknown-status") is None


def test_validation_result_initializes_empty_lists():
    result = api.ValidationResult(status=api.ResultStatus.SUCCESS, entry_id="x")
    assert result.errors == []
    assert result.warnings == []


def test_score_entry_rejects_mutually_exclusive_flags():
    result = api.score_entry(entry_id=None, auto_qualify=True, all_entries=True)
    assert result.status == api.ResultStatus.ERROR
    assert "mutually exclusive" in (result.error or "")


def test_advance_entry_requires_entry_id():
    result = api.advance_entry(entry_id="")
    assert result.status == api.ResultStatus.ERROR
    assert "entry_id required" in (result.error or "")


def test_load_precedent_registry_structure():
    result = api.load_precedent_registry()
    assert result.status == api.ResultStatus.SUCCESS
    assert result.version is not None
    # Three named precedent processes.
    assert set(result.precedents) == {"application_genesis", "evaluative_authority", "standards"}
    # Four boundary conditions a domain must meet.
    assert len(result.boundary_conditions) == 4
    # All three domains present; only the demonstrated instance is marked so.
    assert set(result.domains) == {"academic", "market", "engineering"}
    assert result.domains["academic"]["sgo"]["validation_status"] == "demonstrated"


def test_load_precedent_registry_domain_filter():
    result = api.load_precedent_registry(domain="academic")
    assert result.status == api.ResultStatus.SUCCESS
    assert set(result.domains) == {"academic"}
    assert "sgo" in result.domains["academic"]
    # Precedents and boundary conditions remain available alongside the filter.
    assert len(result.boundary_conditions) == 4


def test_load_precedent_registry_unknown_domain():
    result = api.load_precedent_registry(domain="nonexistent")
    assert result.status == api.ResultStatus.ERROR
    assert "unknown domain" in (result.error or "")


def test_load_precedent_registry_missing_file(tmp_path):
    missing = tmp_path / "no-registry.yaml"
    result = api.load_precedent_registry(registry_path=missing)
    assert result.status == api.ResultStatus.ERROR
    assert "not found" in (result.error or "")
    # Graceful structured error, never a traceback.
    assert result.domains is None


def test_load_precedent_registry_malformed_file(tmp_path):
    bad = tmp_path / "bad-registry.yaml"
    bad.write_text("- just\n- a\n- list\n")
    result = api.load_precedent_registry(registry_path=bad)
    assert result.status == api.ResultStatus.ERROR
    assert "mapping" in (result.error or "")
