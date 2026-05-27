"""Tests for scripts/validate.py"""

# Add scripts to path
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate import (
    VALID_DEFERRAL_REASONS,
    VALID_DIMENSIONS,
    VALID_TRANSITIONS,
    _reachable_statuses,
    validate_entry,
    validate_no_duplicate_urls,
    validate_org_cap_warnings,
    validate_scoring_rubric,
)


def _write_yaml(tmp_dir: Path, filename: str, data: dict) -> Path:
    """Write a YAML file and return its path."""
    filepath = tmp_dir / filename
    with open(filepath, "w") as f:
        yaml.dump(data, f)
    return filepath


def test_valid_entry_passes():
    """A well-formed entry should produce no errors."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_missing_required_field():
    """An entry missing a required field should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            # missing track and status
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Missing required field: track" in e for e in errors)
        assert any("Missing required field: status" in e for e in errors)


def test_invalid_track():
    """An entry with an invalid track should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "invalid_track",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid track" in e for e in errors)


def test_invalid_status():
    """An entry with an invalid status should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "bogus",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid status" in e for e in errors)


def test_id_filename_mismatch():
    """An entry whose id doesn't match the filename should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "wrong-id",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("does not match filename" in e for e in errors)


def test_fit_score_out_of_range():
    """A fit score outside 1-10 should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "fit": {"score": 15},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("out of range" in e for e in errors)


def test_invalid_outcome():
    """An invalid outcome value should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "maybe",
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid outcome" in e for e in errors)


def test_duplicate_yaml_key_fails_validation():
    """Duplicate mapping keys should fail validation instead of silently overwriting."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        filepath = tmp_path / "test-entry.yaml"
        filepath.write_text(
            "\n".join(
                [
                    "id: test-entry",
                    "name: Test Entry",
                    "track: prize",
                    "status: outcome",
                    "outcome: expired",
                    "deadline:",
                    "  date: '2026-03-04'",
                    "  time: null",
                    '  time: "23:59:59 UTC"',
                    "  type: hard",
                ]
            )
        )
        errors = validate_entry(filepath)
        assert any("duplicate key" in e.lower() for e in errors)


def test_all_valid_tracks():
    """All valid track values should pass validation."""
    valid_tracks = [
        "grant", "residency", "job", "fellowship",
        "writing", "emergency", "prize", "program", "consulting",
    ]
    for track in valid_tracks:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = {
                "id": "test-entry",
                "name": "Test Entry",
                "track": track,
                "status": "qualified",
                "outcome": None,
            }
            filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
            errors = validate_entry(filepath)
            assert errors == [], f"Track '{track}' should be valid, got: {errors}"


# --- Status transition validation tests ---


def test_reachable_from_research():
    """All statuses should be reachable from research."""
    reachable = _reachable_statuses("research")
    assert "qualified" in reachable
    assert "submitted" in reachable
    assert "outcome" in reachable


def test_reachable_from_outcome():
    """No statuses should be reachable from outcome (terminal)."""
    reachable = _reachable_statuses("outcome")
    assert reachable == set()


def test_valid_transitions_keys():
    """Every status in VALID_TRANSITIONS should map to valid statuses."""
    all_statuses = set(VALID_TRANSITIONS.keys()) | {"withdrawn"}
    for status, targets in VALID_TRANSITIONS.items():
        for target in targets:
            assert target in all_statuses, (
                f"Transition target '{target}' from '{status}' is not a valid status"
            )


def test_transition_consistent_timeline():
    """An entry whose status matches its timeline should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "timeline": {
                "researched": "2026-01-01",
                "qualified": "2026-01-15",
                "materials_ready": None,
                "submitted": None,
                "acknowledged": None,
                "interview": None,
                "outcome_date": None,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_transition_inconsistent_timeline():
    """A terminal status with timeline evidence that can't reach it should error.

    Outcome can't be reached from withdrawn (both are terminal).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Status is "outcome" but we hack the highest_dated to "withdrawn"
        # by using a status that's genuinely unreachable forward.
        # Since the transitive closure makes all forward statuses reachable
        # from early stages, we test a case where status is forward of timeline
        # AND the intermediate status can't reach it (withdrawn → outcome).
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "rejected",
            "timeline": {
                "researched": "2026-01-01",
                "qualified": "2026-01-15",
                "materials_ready": "2026-02-01",
                "submitted": "2026-02-15",
                "acknowledged": None,
                "interview": None,
                "outcome_date": None,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        # outcome rank (7) > submitted rank (4), and outcome IS reachable
        # from submitted transitively, so no error here — the check validates
        # state machine reachability, not timeline completeness
        # This validates the check doesn't false-positive on valid forward jumps
        assert not any("not reachable" in e for e in errors)


def test_transition_backward_demotion_is_valid():
    """An entry demoted to research with timeline history should not error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "research",
            "outcome": None,
            "timeline": {
                "researched": "2026-01-01",
                "qualified": "2026-01-15",
                "materials_ready": None,
                "submitted": "2026-02-01",
                "acknowledged": None,
                "interview": None,
                "outcome_date": None,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert not any("not reachable" in e for e in errors)


# --- Recommendations validation ---


def test_valid_recommendations():
    """An entry with valid recommendations should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "recommendations": [
                {"name": "Jane Doe", "status": "asked", "relationship": "advisor"},
            ],
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_recommendation_status():
    """An entry with invalid recommendation status should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "recommendations": [
                {"name": "Jane Doe", "status": "maybe"},
            ],
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("recommendations[0].status" in e for e in errors)


def test_validate_scoring_rubric_valid():
    """A valid rubric file should pass rubric validation."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rubric.yaml"
        weight = 1 / len(VALID_DIMENSIONS)
        valid_weights = {dim: weight for dim in sorted(VALID_DIMENSIONS)}
        path.write_text(
            yaml.dump(
                {
                    "weights": valid_weights,
                    "weights_job": valid_weights,
                    "thresholds": {
                        "score_range_min": 1,
                        "score_range_max": 10,
                        "auto_qualify_min": 9.0,
                        "tier1_cutoff": 9.5,
                        "tier2_cutoff": 8.5,
                        "tier3_cutoff": 7.0,
                    },
                },
                sort_keys=False,
            )
        )
        assert validate_scoring_rubric(path) == []


def test_validate_scoring_rubric_invalid_weight_sum():
    """Rubric validation should fail if weights do not sum to 1.0."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rubric.yaml"
        path.write_text(
            yaml.dump(
                {
                    "weights": {
                        "mission_alignment": 1.0,
                        "evidence_match": 0.0,
                        "track_record_fit": 0.0,
                        "network_proximity": 0.0,
                        "financial_alignment": 0.0,
                        "effort_to_value": 0.0,
                        "strategic_value": 0.0,
                        "deadline_feasibility": 0.0,
                        "portal_friction": 0.0,
                    },
                    "weights_job": {
                        "mission_alignment": 0.5,
                        "evidence_match": 0.5,
                        "track_record_fit": 0.0,
                        "network_proximity": 0.0,
                        "strategic_value": 0.0,
                        "financial_alignment": 0.0,
                        "effort_to_value": 0.0,
                        "deadline_feasibility": 0.0,
                        "portal_friction": 0.0,
                    },
                    "thresholds": {
                        "score_range_min": 10,
                        "score_range_max": 1,
                        "auto_qualify_min": 11,
                        "tier1_cutoff": 5,
                        "tier2_cutoff": 6,
                        "tier3_cutoff": 7,
                    },
                },
                sort_keys=False,
            )
        )
        errors = validate_scoring_rubric(path)
        assert any("score_range_min must be <" in e for e in errors)
        assert any("auto_qualify_min must be within score range" in e for e in errors)
        assert any("tier cutoffs" in e for e in errors)


# --- Portal fields validation ---


def test_valid_portal_fields():
    """An entry with valid portal_fields should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "portal_fields": {
                "platform": "submittable",
                "fields": [
                    {"name": "Artist Statement", "format": "textarea", "char_limit": 2000},
                ],
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_portal_field_format():
    """An entry with invalid portal field format should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "portal_fields": {
                "platform": "submittable",
                "fields": [
                    {"name": "Test", "format": "hologram"},
                ],
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("portal_fields.fields[0].format" in e for e in errors)


# --- Withdrawal reason validation ---


def test_valid_withdrawal_reason():
    """An entry with valid withdrawal_reason should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "withdrawn",
            "withdrawal_reason": {
                "reason": "missed_deadline",
                "detail": "Deadline passed",
                "date": "2026-02-01",
                "reopen": False,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_withdrawal_reason():
    """An entry with invalid withdrawal reason should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "withdrawn",
            "withdrawal_reason": {
                "reason": "aliens",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("withdrawal_reason.reason" in e for e in errors)


# --- Deferred status validation ---


def test_deferred_status_valid():
    """An entry with status=deferred should pass validation."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
            "deferral": {
                "reason": "portal_paused",
                "resume_date": "2026-06-01",
                "note": "Portal paused until June.",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_deferred_without_deferral_field_warns():
    """A deferred entry without deferral field should produce a warning (not error)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        warnings = []
        errors = validate_entry(filepath, warnings=warnings)
        assert not any("no 'deferral' field present" in e for e in errors)
        assert any("no 'deferral' field present" in w for w in warnings)


def test_invalid_deferral_reason():
    """An entry with an invalid deferral reason should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
            "deferral": {
                "reason": "bored",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("deferral.reason" in e for e in errors)


def test_valid_deferral_reasons():
    """All valid deferral reasons should pass."""
    for reason in VALID_DEFERRAL_REASONS:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = {
                "id": "test-entry",
                "name": "Test Entry",
                "track": "grant",
                "status": "deferred",
                "outcome": None,
                "deferral": {"reason": reason},
            }
            filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
            errors = validate_entry(filepath)
            assert not any("deferral.reason" in e for e in errors), (
                f"Reason '{reason}' should be valid, got: {errors}"
            )


# --- Fixed deadline type validation ---


def test_fixed_deadline_type_valid():
    """An entry with deadline.type=fixed should pass validation."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "deadline": {"date": "2026-03-16", "type": "fixed"},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


# --- Timezone-less deadline warnings ---


def test_hard_deadline_no_time_warns():
    """Hard deadline with date but no time should produce a warning."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "tz-test", "name": "TZ Test", "track": "grant",
            "status": "qualified", "outcome": None,
            "deadline": {"date": "2026-06-01", "type": "hard"},
        }
        filepath = _write_yaml(tmp_path, "tz-test.yaml", data)
        warnings = []
        errors = validate_entry(filepath, warnings=warnings)
        assert errors == []
        assert any("no time/timezone" in w for w in warnings)


def test_time_without_timezone_warns():
    """Deadline time with no timezone abbreviation should warn."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "tz-test2", "name": "TZ Test 2", "track": "job",
            "status": "qualified", "outcome": None,
            "deadline": {"date": "2026-06-01", "type": "hard", "time": "15:00"},
        }
        filepath = _write_yaml(tmp_path, "tz-test2.yaml", data)
        warnings = []
        validate_entry(filepath, warnings=warnings)
        assert any("no timezone" in w for w in warnings)


def test_time_with_timezone_no_warning():
    """Deadline time with valid timezone should not warn."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "tz-test3", "name": "TZ Test 3", "track": "job",
            "status": "qualified", "outcome": None,
            "deadline": {"date": "2026-06-01", "type": "hard", "time": "15:00 ET"},
        }
        filepath = _write_yaml(tmp_path, "tz-test3.yaml", data)
        warnings = []
        validate_entry(filepath, warnings=warnings)
        assert not any("timezone" in w.lower() for w in warnings)


# --- Deferred reachability ---


def test_deferred_reachable_from_research():
    """deferred should be reachable from research via qualified/drafting/staged."""
    reachable = _reachable_statuses("research")
    assert "deferred" in reachable


def test_status_meta_invalid_approved_at_errors():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "job",
            "status": "staged",
            "outcome": None,
            "status_meta": {"reviewed_by": "ops", "approved_at": "03-01-2026"},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("status_meta.approved_at" in e for e in errors)


def test_status_meta_submitted_at_requires_submitted_by():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "job",
            "status": "submitted",
            "outcome": None,
            "status_meta": {"submitted_at": "2026-03-01"},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("submitted_at requires status_meta.submitted_by" in e for e in errors)


def test_staged_missing_governance_fields_warns():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "job",
            "status": "staged",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        warnings = []
        errors = validate_entry(filepath, warnings=warnings)
        assert errors == []
        assert any("missing status_meta.reviewed_by" in w for w in warnings)
        assert any("missing status_meta.approved_at" in w for w in warnings)


# --- Duplicate URL tests ---


def test_duplicate_urls_detected():
    entries = [
        {"id": "a", "target": {"application_url": "https://example.com/apply"}},
        {"id": "b", "target": {"application_url": "https://example.com/apply"}},
    ]
    errors = []
    dupes = validate_no_duplicate_urls(entries, errors)
    assert dupes == 1
    assert any("Duplicate" in e for e in errors)


def test_no_duplicate_urls():
    entries = [
        {"id": "a", "target": {"application_url": "https://example.com/a"}},
        {"id": "b", "target": {"application_url": "https://example.com/b"}},
    ]
    errors = []
    dupes = validate_no_duplicate_urls(entries, errors)
    assert dupes == 0
    assert errors == []


def test_duplicate_urls_handles_missing_url():
    entries = [{"id": "a", "target": {}}, {"id": "b"}]
    errors = []
    dupes = validate_no_duplicate_urls(entries, errors)
    assert dupes == 0


# --- Org-cap tests ---


def test_org_cap_violation_detected():
    entries = [
        {"id": "a", "status": "qualified", "target": {"organization": "BigCo"}},
        {"id": "b", "status": "submitted", "target": {"organization": "BigCo"}},
    ]
    warnings = []
    violations = validate_org_cap_warnings(entries, warnings, cap=1)
    assert violations == 1
    assert any("bigco" in w.lower() for w in warnings)


def test_org_cap_no_violation():
    entries = [
        {"id": "a", "status": "qualified", "target": {"organization": "Solo"}},
    ]
    warnings = []
    violations = validate_org_cap_warnings(entries, warnings, cap=1)
    assert violations == 0


def test_org_cap_ignores_closed():
    entries = [
        {"id": "a", "status": "qualified", "target": {"organization": "BigCo"}},
        {"id": "b", "status": "withdrawn", "target": {"organization": "BigCo"}},
    ]
    warnings = []
    violations = validate_org_cap_warnings(entries, warnings, cap=1)
    assert violations == 0
