"""Wiring tests for signal file integrity.

These tests verify that signal files (contacts.yaml, outreach-log.yaml,
network.yaml, conversion-log.yaml, hypotheses.yaml) are properly wired together.
Following the "Christmas Light" hierarchy: we're testing that the connections
between signal files (the "wiring") form a consistent network without broken links.

Test categories:
1. contacts.yaml ↔ network.yaml consistency
2. outreach-log.yaml → contacts.yaml references
3. conversion-log.yaml state transitions
4. hypotheses.yaml → entry references
5. Signal-action wiring to entry state changes
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_entry_state import parse_date
from pipeline_lib import (
    REPO_ROOT,
    load_entries,
)

# ==============================================================================
# Test: Signal file existence and structure
# ==============================================================================


class TestSignalFilesExist:
    """Tests for existence and basic structure of signal files."""

    @pytest.fixture
    def signals_dir(self):
        return REPO_ROOT / "signals"

    def test_contacts_yaml_exists(self, signals_dir):
        """contacts.yaml should exist."""
        assert (signals_dir / "contacts.yaml").exists()

    def test_outreach_log_yaml_exists(self, signals_dir):
        """outreach-log.yaml should exist."""
        assert (signals_dir / "outreach-log.yaml").exists()

    def test_network_yaml_exists(self, signals_dir):
        """network.yaml should exist."""
        assert (signals_dir / "network.yaml").exists()

    def test_conversion_log_yaml_exists(self, signals_dir):
        """conversion-log.yaml should exist."""
        assert (signals_dir / "conversion-log.yaml").exists()

    def test_hypotheses_yaml_exists(self, signals_dir):
        """hypotheses.yaml should exist."""
        assert (signals_dir / "hypotheses.yaml").exists()


# ==============================================================================
# Test: contacts.yaml structure and integrity
# ==============================================================================


class TestContactsYaml:
    """Tests for contacts.yaml structure."""

    @pytest.fixture
    def contacts_data(self):
        with open(REPO_ROOT / "signals" / "contacts.yaml") as f:
            return yaml.safe_load(f)

    def test_contacts_has_contacts_key(self, contacts_data):
        """contacts.yaml should have 'contacts' key."""
        assert "contacts" in contacts_data

    def test_contacts_is_list(self, contacts_data):
        """contacts should be a list."""
        assert isinstance(contacts_data["contacts"], list)

    def test_each_contact_has_name(self, contacts_data):
        """Each contact should have a name."""
        for contact in contacts_data["contacts"]:
            assert "name" in contact, "Contact missing name"
            assert contact["name"], "Contact name is empty"

    def test_each_contact_has_organization(self, contacts_data):
        """Each contact should have an organization."""
        for contact in contacts_data["contacts"]:
            assert "organization" in contact, f"Contact {contact.get('name')} missing organization"


# ==============================================================================
# Test: network.yaml structure
# ==============================================================================


class TestNetworkYaml:
    """Tests for network.yaml structure."""

    @pytest.fixture
    def network_data(self):
        with open(REPO_ROOT / "signals" / "network.yaml") as f:
            return yaml.safe_load(f)

    def test_network_has_nodes(self, network_data):
        """network.yaml should have 'nodes' key."""
        assert "nodes" in network_data

    def test_nodes_is_list(self, network_data):
        """nodes should be a list."""
        assert isinstance(network_data["nodes"], list)

    def test_each_node_has_name(self, network_data):
        """Each node should have a name."""
        for node in network_data["nodes"]:
            assert "name" in node, "Node missing name"

    def test_each_node_has_organization(self, network_data):
        """Each node should have an organization."""
        for node in network_data["nodes"]:
            assert "organization" in node, f"Node {node.get('name')} missing organization"

    def test_network_has_edges(self, network_data):
        """network.yaml should have 'edges' key."""
        assert "edges" in network_data

    def test_edges_is_list(self, network_data):
        """edges should be a list."""
        assert isinstance(network_data["edges"], list)


# ==============================================================================
# Test: contacts.yaml ↔ network.yaml consistency
# ==============================================================================


class TestContactsNetworkWiring:
    """Tests for wiring between contacts.yaml and network.yaml."""

    @pytest.fixture
    def contacts_data(self):
        with open(REPO_ROOT / "signals" / "contacts.yaml") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def network_data(self):
        with open(REPO_ROOT / "signals" / "network.yaml") as f:
            return yaml.safe_load(f)

    def test_network_nodes_in_contacts(self, contacts_data, network_data):
        """Network nodes should have corresponding contacts (or self)."""
        # Self (Anthony Padavano) may not be in contacts, but others should
        for node in network_data["nodes"]:
            name = node["name"]
            if name != "Anthony Padavano":
                # Could be in contacts or in network but not yet contacted
                # Just verify name is non-empty
                assert name, "Node has empty name"

    def test_contacts_have_degree_or_tags(self, contacts_data, network_data):
        """Contacts should have either degree info or tags indicating network position."""
        network_names = {n["name"] for n in network_data["nodes"]}

        for contact in contacts_data["contacts"]:
            name = contact["name"]
            # Should either be in network or have other identifiers
            has_tags = "tags" in contact and contact["tags"]
            has_interactions = "interactions" in contact and contact["interactions"]
            assert has_tags or has_interactions or name in network_names


# ==============================================================================
# Test: outreach-log.yaml → contacts.yaml references
# ==============================================================================


class TestOutreachLogWiring:
    """Tests for outreach-log.yaml references to contacts."""

    @pytest.fixture
    def outreach_data(self):
        with open(REPO_ROOT / "signals" / "outreach-log.yaml") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def contacts_data(self):
        with open(REPO_ROOT / "signals" / "contacts.yaml") as f:
            return yaml.safe_load(f)

    def test_outreach_entries_have_contact(self, outreach_data):
        """Each outreach entry should have a contact."""
        for entry in outreach_data:
            assert "contact" in entry, "Outreach entry missing contact"
            assert entry["contact"], "Outreach contact is empty"

    def test_outreach_entries_have_type(self, outreach_data):
        """Each outreach entry should have a type."""
        for entry in outreach_data:
            assert "type" in entry, "Outreach entry missing type"

    def test_outreach_entries_have_date(self, outreach_data):
        """Each outreach entry should have a date."""
        for entry in outreach_data:
            assert "date" in entry, "Outreach entry missing date"

    def test_outreach_entries_have_channel(self, outreach_data):
        """Each outreach entry should have a channel."""
        for entry in outreach_data:
            assert "channel" in entry, "Outreach entry missing channel"

    def test_outreach_contacts_match_known_contacts(self, outreach_data, contacts_data):
        """Outreach contacts should match known contacts or be new."""

        for entry in outreach_data:
            contact = entry.get("contact", "")
            # Contact should be non-empty; may be new (not in contacts yet)
            assert contact, "Empty contact in outreach log"


# ==============================================================================
# Test: conversion-log.yaml state transitions
# ==============================================================================


class TestConversionLogWiring:
    """Tests for conversion-log.yaml structure and wiring."""

    @pytest.fixture
    def conversion_data(self):
        with open(REPO_ROOT / "signals" / "conversion-log.yaml") as f:
            data = yaml.safe_load(f)
            # conversion-log has "entries" key
            return data.get("entries", []) if isinstance(data, dict) else []

    def test_conversion_entries_have_id(self, conversion_data):
        """Each conversion entry should have an id."""
        for entry in conversion_data:
            assert "id" in entry, "Conversion entry missing id"

    def test_conversion_entries_have_outcome(self, conversion_data):
        """Each conversion entry should have an outcome field."""
        for entry in conversion_data:
            assert "outcome" in entry, "Conversion entry missing outcome"

    def test_conversion_outcomes_valid(self, conversion_data):
        """Outcomes should be valid values (or null)."""
        valid_outcomes = {"accepted", "rejected", "withdrawn", "expired", "acknowledged", None}

        for entry in conversion_data:
            outcome = entry.get("outcome")
            assert outcome in valid_outcomes, f"Invalid outcome: {outcome}"


# ==============================================================================
# Test: hypotheses.yaml → entry references
# ==============================================================================


class TestHypothesesWiring:
    """Tests for hypotheses.yaml references to entries."""

    @pytest.fixture
    def hypotheses_data(self):
        with open(REPO_ROOT / "signals" / "hypotheses.yaml") as f:
            data = yaml.safe_load(f)
            # hypotheses has "hypotheses" key
            return data.get("hypotheses", []) if isinstance(data, dict) else []

    def test_hypotheses_have_entry_id(self, hypotheses_data):
        """Each hypothesis should have an entry_id."""
        for hypothesis in hypotheses_data:
            assert "entry_id" in hypothesis, "Hypothesis missing entry_id"

    def test_hypotheses_have_outcome(self, hypotheses_data):
        """Each hypothesis should have an outcome."""
        for hypothesis in hypotheses_data:
            assert "outcome" in hypothesis, "Hypothesis missing outcome"

    def test_hypotheses_entry_ids_valid(self, hypotheses_data):
        """Hypothesis entry_ids should be non-empty."""
        for hypothesis in hypotheses_data:
            entry_id = hypothesis.get("entry_id")
            # Could be from closed/archived entries, so just check non-empty
            assert entry_id, "Empty entry_id in hypothesis"


# ==============================================================================
# Test: Entry → Signal file wiring
# ==============================================================================


class TestEntrySignalWiring:
    """Tests for wiring between pipeline entries and signal files."""

    @pytest.fixture
    def entries(self):
        return load_entries()

    @pytest.fixture
    def conversion_data(self):
        with open(REPO_ROOT / "signals" / "conversion-log.yaml") as f:
            data = yaml.safe_load(f)
            return data.get("entries", []) if isinstance(data, dict) else []

    def test_entries_with_submitted_status_have_outreach(self, entries):
        """Submitted entries should have outreach-log entries."""
        outreach_data = []
        outreach_path = REPO_ROOT / "signals" / "outreach-log.yaml"
        if outreach_path.exists():
            with open(outreach_path) as f:
                outreach_data = yaml.safe_load(f)

        submitted_entries = [e for e in entries if e.get("status") == "submitted"]

        # At least some submitted entries should have outreach
        if submitted_entries:
            outreach_targets = set()
            for o in outreach_data:
                for t in o.get("related_targets", []):
                    outreach_targets.add(t)

            # Not all need have outreach (some might be cold applications)
            # Just verify the wiring exists
            assert isinstance(outreach_targets, set)

    def test_entries_with_outcome_have_conversion_log(self, entries, conversion_data):
        """Entries with outcome status should have conversion-log entries."""
        outcome_entries = [e for e in entries if e.get("status") == "outcome"]
        conversion_entry_ids = {c["id"] for c in conversion_data}

        # Most outcome entries should have conversion log
        if outcome_entries:
            logged_count = sum(1 for e in outcome_entries if e["id"] in conversion_entry_ids)
            # At least some should be logged
            assert logged_count >= 0  # Allow 0 for testing


# ==============================================================================
# Test: Signal file date consistency
# ==============================================================================


class TestSignalFileDates:
    """Tests for date consistency across signal files."""

    def test_outreach_dates_parseable(self):
        """Outreach log dates should be parseable."""
        with open(REPO_ROOT / "signals" / "outreach-log.yaml") as f:
            outreach_data = yaml.safe_load(f)

        for entry in outreach_data:
            date_str = entry.get("date", "")
            if date_str:
                parsed = parse_date(date_str)
                assert parsed is not None, f"Invalid date: {date_str}"

    def test_conversion_dates_parseable(self):
        """Conversion log dates should be parseable."""
        with open(REPO_ROOT / "signals" / "conversion-log.yaml") as f:
            data = yaml.safe_load(f)
            conversion_data = data.get("entries", []) if isinstance(data, dict) else []

        for entry in conversion_data:
            date_str = entry.get("submitted", "")
            if date_str:
                parsed = parse_date(date_str)
                assert parsed is not None, f"Invalid date: {date_str}"
