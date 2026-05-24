#!/usr/bin/env python3
"""Tests for validate_signals.py — signal YAML schema validation."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


from validate_signals import (
    AGENT_MODES,
    OUTCOMES,
    OUTREACH_CHANNELS,
    OUTREACH_TYPES,
    SIGNAL_TYPES,
    validate_agent_actions,
    validate_all_signals,
    validate_contacts,
    validate_conversion_log,
    validate_hypotheses,
    validate_network,
    validate_outreach_log,
    validate_referential_integrity,
    validate_signal_actions,
)


@pytest.fixture()
def signals_dir(tmp_path, monkeypatch):
    """Create a temp signals directory and patch SIGNALS_DIR."""
    import validate_signals
    monkeypatch.setattr(validate_signals, "SIGNALS_DIR", tmp_path)
    return tmp_path


def _write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f)


def test_signal_actions_valid(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{
            "signal_id": "test-001",
            "signal_type": "hypothesis",
            "description": "Test signal",
            "triggered_action": "advance to drafting",
            "action_date": "2026-03-04",
        }]
    })
    errors = []
    count = validate_signal_actions(errors)
    assert count == 1
    assert errors == []


def test_signal_actions_missing_field(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{"signal_id": "test"}]
    })
    errors = []
    validate_signal_actions(errors)
    assert len(errors) >= 3  # missing description, triggered_action, signal_type, action_date


def test_signal_actions_invalid_type(signals_dir):
    _write_yaml(signals_dir / "signal-actions.yaml", {
        "actions": [{
            "signal_id": "test",
            "signal_type": "invalid_type",
            "description": "Test",
            "triggered_action": "advance",
            "action_date": "2026-03-04",
        }]
    })
    errors = []
    validate_signal_actions(errors)
    assert any("signal_type" in e for e in errors)


def test_conversion_log_valid(signals_dir):
    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{
            "id": "anthropic-se",
            "submitted": "2026-02-24",
            "track": "job",
            "outcome": None,
        }]
    })
    errors = []
    count = validate_conversion_log(errors)
    assert count == 1
    assert errors == []


def test_conversion_log_invalid_outcome(signals_dir):
    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{
            "id": "test",
            "submitted": "2026-02-24",
            "track": "job",
            "outcome": "invalid_outcome",
        }]
    })
    errors = []
    validate_conversion_log(errors)
    assert any("outcome" in e for e in errors)


def test_hypotheses_valid(signals_dir):
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{
            "entry_id": "anthropic-se",
            "category": "timing",
        }]
    })
    errors = []
    count = validate_hypotheses(errors)
    assert count == 1
    assert errors == []


def test_agent_actions_valid(signals_dir):
    _write_yaml(signals_dir / "agent-actions.yaml", {
        "runs": [{
            "timestamp": "2026-03-03T07:00:00",
            "mode": "execute",
        }]
    })
    errors = []
    count = validate_agent_actions(errors)
    assert count == 1
    assert errors == []


def test_missing_file(signals_dir):
    errors = []
    count = validate_signal_actions(errors)
    assert count == 0
    assert any("missing" in e for e in errors)


def test_validate_all_returns_stats(signals_dir):
    # Create minimal valid files
    _write_yaml(signals_dir / "signal-actions.yaml", {"actions": []})
    _write_yaml(signals_dir / "conversion-log.yaml", {"entries": []})
    _write_yaml(signals_dir / "hypotheses.yaml", {"hypotheses": []})
    _write_yaml(signals_dir / "agent-actions.yaml", {"runs": []})
    errors, stats = validate_all_signals()
    assert isinstance(errors, list)
    assert isinstance(stats, dict)
    assert "signal-actions" in stats


def test_constants_populated():
    assert len(SIGNAL_TYPES) >= 5
    assert None in OUTCOMES
    assert "execute" in AGENT_MODES


# --- Referential integrity tests ---


def test_referential_integrity_valid(signals_dir, tmp_path, monkeypatch):
    """Valid references produce no errors."""
    import validate_signals

    # Create a fake pipeline dir with an entry
    pipeline_dir = tmp_path / "pipeline" / "active"
    pipeline_dir.mkdir(parents=True)
    _write_yaml(pipeline_dir / "test-entry.yaml", {"id": "test-entry", "status": "staged"})
    monkeypatch.setattr(validate_signals, "ALL_PIPELINE_DIRS_WITH_POOL", [pipeline_dir])

    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{"id": "test-entry", "submitted": "2026-03-01", "track": "job"}]
    })
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{"entry_id": "test-entry", "category": "timing"}]
    })
    errors = []
    dangling = validate_referential_integrity(errors)
    assert dangling == 0
    assert errors == []


def test_referential_integrity_dangling(signals_dir, tmp_path, monkeypatch):
    """Dangling conversion-log/hypotheses references are counted as warnings.

    They are deliberately NOT errors: historical signal records legitimately
    reference archived/purged entries (the real repo has ~18 such refs), so
    surfacing them as errors would break the signal-validation gate. The
    function returns the dangling count without appending to `errors`.
    """
    import validate_signals

    pipeline_dir = tmp_path / "pipeline" / "active"
    pipeline_dir.mkdir(parents=True)
    monkeypatch.setattr(validate_signals, "ALL_PIPELINE_DIRS_WITH_POOL", [pipeline_dir])

    _write_yaml(signals_dir / "conversion-log.yaml", {
        "entries": [{"id": "nonexistent", "submitted": "2026-03-01", "track": "job"}]
    })
    _write_yaml(signals_dir / "hypotheses.yaml", {
        "hypotheses": [{"id": "also-missing", "category": "timing"}]
    })
    errors = []
    dangling = validate_referential_integrity(errors)
    assert dangling == 2  # both counted
    assert errors == []  # ...but reported as warnings, not errors


# --- Contacts validation tests ---


def test_contacts_valid(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{
            "name": "Jane Doe",
            "channel": "linkedin",
            "interactions": [{"date": "2026-03-01", "type": "connect", "note": "DM sent"}],
        }]
    })
    errors = []
    count = validate_contacts(errors)
    assert count == 1
    assert errors == []


def test_contacts_invalid_channel(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{"name": "Jane", "channel": "fax"}]
    })
    errors = []
    validate_contacts(errors)
    assert any("channel" in e for e in errors)


def test_contacts_missing_name(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{"channel": "email"}]
    })
    errors = []
    validate_contacts(errors)
    assert any("name" in e for e in errors)


def test_contacts_optional_missing_file(signals_dir):
    errors = []
    count = validate_contacts(errors)
    assert count == 0
    assert errors == []


def test_contacts_bad_date(signals_dir):
    _write_yaml(signals_dir / "contacts.yaml", {
        "contacts": [{
            "name": "Bob",
            "interactions": [{"date": "not-a-date", "type": "call"}],
        }]
    })
    errors = []
    validate_contacts(errors)
    assert any("not-a-date" in e for e in errors)


# --- Outreach log tests ---


def test_outreach_log_valid(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "2026-03-17",
            "type": "post_submission",
            "contact": "Jane Smith",
            "channel": "linkedin",
            "note": "Connection request sent",
            "related_targets": ["test-entry-1"],
        }]
    })
    errors = []
    count = validate_outreach_log(errors)
    assert count == 1
    assert errors == []


def test_outreach_log_missing_contact(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "2026-03-17",
            "type": "reconnect",
            "channel": "linkedin",
            "note": "No contact field",
        }]
    })
    errors = []
    validate_outreach_log(errors)
    assert any("contact" in e for e in errors)


def test_outreach_log_invalid_type(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "2026-03-17",
            "type": "invalid_type",
            "contact": "Jane",
            "channel": "linkedin",
        }]
    })
    errors = []
    validate_outreach_log(errors)
    assert any("type" in e for e in errors)


def test_outreach_log_invalid_channel(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "2026-03-17",
            "type": "seed",
            "contact": "Jane",
            "channel": "telegram",
        }]
    })
    errors = []
    validate_outreach_log(errors)
    assert any("channel" in e for e in errors)


def test_outreach_log_bad_date(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "not-a-date",
            "type": "seed",
            "contact": "Jane",
            "channel": "linkedin",
        }]
    })
    errors = []
    validate_outreach_log(errors)
    assert any("date" in e for e in errors)


def test_outreach_log_invalid_targets(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {
        "entries": [{
            "date": "2026-03-17",
            "type": "seed",
            "contact": "Jane",
            "channel": "linkedin",
            "related_targets": "not-a-list",
        }]
    })
    errors = []
    validate_outreach_log(errors)
    assert any("related_targets" in e for e in errors)


def test_outreach_log_missing_file(signals_dir):
    errors = []
    count = validate_outreach_log(errors)
    assert count == 0
    assert errors == []


def test_outreach_log_missing_entries_key(signals_dir):
    _write_yaml(signals_dir / "outreach-log.yaml", {"wrong_key": []})
    errors = []
    validate_outreach_log(errors)
    assert any("entries" in e for e in errors)


# --- Network graph tests ---


def test_network_valid(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [
            {"name": "Alice", "organization": "Acme"},
            {"name": "Bob", "organization": "Widgets"},
        ],
        "edges": [
            {"from": "Alice", "to": "Bob", "strength": 5},
        ],
    })
    errors = []
    count = validate_network(errors)
    assert count == 2
    assert errors == []


def test_network_duplicate_node(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [
            {"name": "Alice", "organization": "Acme"},
            {"name": "Alice", "organization": "Other"},
        ],
        "edges": [],
    })
    errors = []
    validate_network(errors)
    assert any("duplicate" in e for e in errors)


def test_network_edge_missing_from(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [{"name": "Alice"}],
        "edges": [{"to": "Alice", "strength": 3}],
    })
    errors = []
    validate_network(errors)
    assert any("from" in e for e in errors)


def test_network_edge_strength_out_of_range(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [{"name": "Alice"}, {"name": "Bob"}],
        "edges": [{"from": "Alice", "to": "Bob", "strength": 15}],
    })
    errors = []
    validate_network(errors)
    assert any("strength" in e for e in errors)


def test_network_edge_strength_zero(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [{"name": "Alice"}, {"name": "Bob"}],
        "edges": [{"from": "Alice", "to": "Bob", "strength": 0}],
    })
    errors = []
    validate_network(errors)
    assert any("strength" in e for e in errors)


def test_network_missing_file(signals_dir):
    errors = []
    count = validate_network(errors)
    assert count == 0
    assert errors == []


def test_network_nodes_not_list(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {"nodes": "bad", "edges": []})
    errors = []
    validate_network(errors)
    assert any("nodes" in e for e in errors)


def test_network_node_missing_name(signals_dir):
    _write_yaml(signals_dir / "network.yaml", {
        "nodes": [{"organization": "NoName"}],
        "edges": [],
    })
    errors = []
    validate_network(errors)
    assert any("name" in e for e in errors)


def test_validate_all_includes_new_validators(signals_dir):
    """validate_all_signals should include outreach-log and network in stats."""
    _write_yaml(signals_dir / "signal-actions.yaml", {"actions": []})
    _write_yaml(signals_dir / "conversion-log.yaml", {"entries": []})
    _write_yaml(signals_dir / "hypotheses.yaml", {"hypotheses": []})
    _write_yaml(signals_dir / "agent-actions.yaml", {"runs": []})
    _write_yaml(signals_dir / "outreach-log.yaml", {"entries": []})
    _write_yaml(signals_dir / "network.yaml", {"nodes": [], "edges": []})
    errors, stats = validate_all_signals()
    assert "outreach-log" in stats
    assert "network" in stats


def test_outreach_types_constant():
    assert "post_submission" in OUTREACH_TYPES
    assert "reconnect" in OUTREACH_TYPES
    assert "seed" in OUTREACH_TYPES
    assert "dm" in OUTREACH_TYPES


def test_outreach_channels_constant():
    assert "linkedin" in OUTREACH_CHANNELS
    assert "email" in OUTREACH_CHANNELS
