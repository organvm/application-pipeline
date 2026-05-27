"""Tests for scripts/submission_audit.py"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import detect_entry_portal, load_entries
from submission_audit import (
    PRE_SUBMIT_STATUSES,
    SUBMITTABLE_PORTALS,
    _check_answers_complete,
    check_entry,
)

# --- Constants ---


def test_submittable_portals_complete():
    """SUBMITTABLE_PORTALS contains all six expected portal types."""
    expected = {"greenhouse", "ashby", "lever", "custom", "email", "slideroom"}
    assert SUBMITTABLE_PORTALS == expected


def test_pre_submit_statuses():
    """PRE_SUBMIT_STATUSES contains the correct pre-submission statuses."""
    expected = {"research", "qualified", "drafting", "staged", "deferred"}
    assert PRE_SUBMIT_STATUSES == expected


# --- check_entry structure ---


def test_check_entry_returns_dict():
    """check_entry returns dict with expected keys."""
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "status": "staged",
        "target": {
            "organization": "Test Org",
            "portal": "greenhouse",
            "application_url": "https://boards.greenhouse.io/test/jobs/123",
        },
        "submission": {
            "materials_attached": [],
            "variant_ids": {},
        },
    }
    result = check_entry(entry)
    assert isinstance(result, dict)
    assert "id" in result
    assert "portal" in result
    assert "status" in result
    assert "results" in result
    assert "ready" in result
    assert "pass_count" in result
    assert "total_checks" in result
    assert result["id"] == "test-entry"
    assert result["portal"] == "greenhouse"
    assert result["status"] == "staged"
    assert isinstance(result["results"], dict)
    assert isinstance(result["ready"], bool)
    assert isinstance(result["pass_count"], int)
    assert isinstance(result["total_checks"], int)


def test_check_entry_results_keys():
    """check_entry results dict contains expected check names."""
    entry = {
        "id": "test-entry",
        "status": "staged",
        "target": {"portal": "greenhouse", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    result = check_entry(entry)
    expected_keys = {
        "portal_parsed",
        "resume_pdf",
        "cover_letter",
        "status_submittable",
        "review_approved",
        "staged_sla",
        "answer_file",
        "has_target_url",
    }
    assert expected_keys == set(result["results"].keys())


def test_check_entry_pass_count_matches():
    """pass_count equals the number of True values in results."""
    entry = {
        "id": "test-entry",
        "status": "staged",
        "target": {"portal": "custom", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    result = check_entry(entry)
    expected_pass = sum(1 for v in result["results"].values() if v)
    assert result["pass_count"] == expected_pass
    assert result["total_checks"] == len(result["results"])


# --- check_entry with real data ---


def test_check_entry_ready_entry():
    """Load a real greenhouse entry from submitted/ and verify a well-formed result.

    Picks any greenhouse entry dynamically rather than a hardcoded id (which
    drifts as entries are archived/moved).
    """
    from pipeline_lib import PIPELINE_DIR_SUBMITTED
    entries = load_entries(dirs=[PIPELINE_DIR_SUBMITTED])
    greenhouse = [e for e in entries if (e.get("target") or {}).get("portal") == "greenhouse"]
    if not greenhouse:
        pytest.skip("no greenhouse entry in submitted/ to exercise")
    entry = greenhouse[0]

    result = check_entry(entry)
    assert result["id"] == entry.get("id")
    assert result["portal"] == "greenhouse"
    assert result["status"] == entry.get("status")
    assert result["results"]["portal_parsed"] is True
    assert "review_approved" in result["results"]
    assert result["results"]["has_target_url"] is True


# --- _check_answers_complete ---


def test_check_answers_complete_detects_fill_in():
    """_check_answers_complete returns False when answers contain FILL IN placeholders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily point the module's GREENHOUSE_ANSWERS_DIR to our temp dir
        import submission_audit

        orig_dir = submission_audit.GREENHOUSE_ANSWERS_DIR
        try:
            submission_audit.GREENHOUSE_ANSWERS_DIR = Path(tmpdir)

            # Write an answer file with FILL IN placeholder
            answer_file = Path(tmpdir) / "test-entry.yaml"
            answer_file.write_text(yaml.dump({
                "question_1": "My answer is complete.",
                "question_2": "FILL IN your response here",
            }))

            assert _check_answers_complete("greenhouse", "test-entry") is False

            # Now write a clean answer file
            answer_file.write_text(yaml.dump({
                "question_1": "My answer is complete.",
                "question_2": "Another complete answer.",
            }))

            assert _check_answers_complete("greenhouse", "test-entry") is True

        finally:
            submission_audit.GREENHOUSE_ANSWERS_DIR = orig_dir


def test_check_answers_complete_missing_file():
    """_check_answers_complete returns False when answer file does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import submission_audit

        orig_dir = submission_audit.GREENHOUSE_ANSWERS_DIR
        try:
            submission_audit.GREENHOUSE_ANSWERS_DIR = Path(tmpdir)
            assert _check_answers_complete("greenhouse", "nonexistent-entry") is False
        finally:
            submission_audit.GREENHOUSE_ANSWERS_DIR = orig_dir


def test_check_answers_complete_non_ats_portal():
    """_check_answers_complete returns True for non-ATS portals that don't need answer files."""
    assert _check_answers_complete("custom", "any-entry") is True
    assert _check_answers_complete("email", "any-entry") is True
    assert _check_answers_complete("lever", "any-entry") is True


def test_check_answers_complete_detects_todo():
    """_check_answers_complete returns False for TODO placeholder values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import submission_audit

        orig_dir = submission_audit.GREENHOUSE_ANSWERS_DIR
        try:
            submission_audit.GREENHOUSE_ANSWERS_DIR = Path(tmpdir)
            answer_file = Path(tmpdir) / "todo-entry.yaml"
            answer_file.write_text(yaml.dump({
                "question_1": "Complete answer.",
                "question_2": "TODO",
            }))
            assert _check_answers_complete("greenhouse", "todo-entry") is False
        finally:
            submission_audit.GREENHOUSE_ANSWERS_DIR = orig_dir


def test_check_answers_complete_ignores_optional_fill_in_with_required_metadata():
    """Optional placeholders should not fail completeness when required fields are answered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import submission_audit

        orig_dir = submission_audit.GREENHOUSE_ANSWERS_DIR
        try:
            submission_audit.GREENHOUSE_ANSWERS_DIR = Path(tmpdir)
            answer_file = Path(tmpdir) / "meta-entry.yaml"
            answer_file.write_text(
                "# Optional field\n"
                "# Type: text | Optional\n"
                'optional_q: "FILL IN"\n'
                "\n"
                "# Required field\n"
                "# Type: text | Required\n"
                'required_q: "Complete answer"\n'
            )
            assert _check_answers_complete("greenhouse", "meta-entry") is True
        finally:
            submission_audit.GREENHOUSE_ANSWERS_DIR = orig_dir


# --- deep mode ---


def test_deep_mode_adds_checks():
    """deep=True adds auth_configured and answers_complete to results."""
    entry = {
        "id": "test-deep",
        "status": "staged",
        "target": {"portal": "greenhouse", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    # Without deep
    shallow = check_entry(entry, deep=False)
    assert "auth_configured" not in shallow["results"]
    assert "answers_complete" not in shallow["results"]

    # With deep
    deep = check_entry(entry, deep=True, config=None)
    assert "auth_configured" in deep["results"]
    assert "answers_complete" in deep["results"]
    # total_checks should increase
    assert deep["total_checks"] > shallow["total_checks"]
    assert deep["total_checks"] == shallow["total_checks"] + 2


# --- detect_entry_portal ---


def test_detect_entry_portal_uses_pipeline_lib():
    """detect_entry_portal works for entries with explicit portal field."""
    entry = {"target": {"portal": "greenhouse"}}
    assert detect_entry_portal(entry) == "greenhouse"

    entry = {"target": {"portal": "ashby"}}
    assert detect_entry_portal(entry) == "ashby"

    entry = {"target": {"portal": "custom"}}
    assert detect_entry_portal(entry) == "custom"


def test_detect_entry_portal_fallback_to_url():
    """detect_entry_portal falls back to URL-based detection when portal field is empty."""
    entry = {
        "target": {
            "portal": "",
            "application_url": "https://boards.greenhouse.io/company/jobs/123",
        },
    }
    assert detect_entry_portal(entry) == "greenhouse"


def test_detect_entry_portal_unknown():
    """detect_entry_portal returns 'unknown' when no portal info is available."""
    entry = {"target": {"portal": "", "application_url": ""}}
    assert detect_entry_portal(entry) == "unknown"

    entry_no_target = {}
    assert detect_entry_portal(entry_no_target) == "unknown"


# --- Submitted entries are not submittable ---


def test_check_entry_submitted_status_not_submittable():
    """Entries with submitted status fail the status_submittable check."""
    entry = {
        "id": "already-submitted",
        "status": "submitted",
        "target": {"portal": "custom", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    result = check_entry(entry)
    assert result["results"]["status_submittable"] is False
    assert result["ready"] is False


def test_check_entry_staged_requires_approved_at_for_review_gate():
    """Staged entries need reviewed_by + approved_at to pass review_approved."""
    entry = {
        "id": "review-gated",
        "status": "staged",
        "status_meta": {"reviewed_by": "operator"},
        "target": {"portal": "custom", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
        "last_touched": "2099-01-01",
    }
    result = check_entry(entry)
    assert result["results"]["review_approved"] is False

    entry["status_meta"]["approved_at"] = "2099-01-01"
    result_ok = check_entry(entry)
    assert result_ok["results"]["review_approved"] is True


def test_check_entry_staged_sla_violates_after_72_hours():
    """Staged entries older than 72h should fail staged_sla check."""
    entry = {
        "id": "sla-breach",
        "status": "staged",
        "status_meta": {"reviewed_by": "op", "approved_at": "2099-01-01"},
        "target": {"portal": "custom", "application_url": "https://example.com"},
        "submission": {"materials_attached": [], "variant_ids": {}},
        "last_touched": "2000-01-01",
    }
    result = check_entry(entry)
    assert result["results"]["staged_sla"] is False
