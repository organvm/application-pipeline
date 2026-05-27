#!/usr/bin/env python3
"""Validate schema integrity of signal YAML files.

Checks signals/signal-actions.yaml, signals/conversion-log.yaml,
signals/hypotheses.yaml, and signals/agent-actions.yaml against
their expected schemas.

Usage:
    python scripts/validate_signals.py              # Report only (always exit 0)
    python scripts/validate_signals.py --strict     # Exit non-zero on any error
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL, SIGNALS_DIR

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SIGNAL_TYPES = {"hypothesis", "score_threshold", "pattern", "agent_rule", "conversion_data", "network_change"}
OUTCOMES = {None, "null", "rejected", "acknowledged", "withdrawn", "expired", "accepted"}
AGENT_MODES = {"plan", "execute"}

# Entry IDs that indicate test data contamination in production signal files
TEST_ENTRY_IDS = {"test-entry", "deferred-entry", "integration-test", "test-integration", "mock-entry", "fake-entry"}


def _load_yaml(path: Path) -> dict | list | None:
    """Load a YAML file, returning None if missing or empty."""
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def _check_str(entry: dict, key: str, errors: list[str], label: str) -> None:
    """Assert a required string field exists."""
    val = entry.get(key)
    if val is None or not isinstance(val, str) or not val.strip():
        errors.append(f"{label}: missing or empty required field '{key}'")


def validate_signal_actions(errors: list[str]) -> int:
    """Validate signals/signal-actions.yaml. Returns entry count."""
    path = SIGNALS_DIR / "signal-actions.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "actions" not in data:
        errors.append(f"{path}: missing top-level 'actions' key")
        return 0
    actions = data["actions"]
    if not isinstance(actions, list):
        errors.append(f"{path}: 'actions' must be a list")
        return 0

    for i, entry in enumerate(actions):
        label = f"{path} [action {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "signal_id", errors, label)
        _check_str(entry, "description", errors, label)
        _check_str(entry, "triggered_action", errors, label)

        # signal_type must be from allowed set
        st = entry.get("signal_type")
        if not isinstance(st, str) or st not in SIGNAL_TYPES:
            errors.append(f"{label}: signal_type '{st}' not in {sorted(SIGNAL_TYPES)}")

        # action_date must be YYYY-MM-DD
        ad = str(entry.get("action_date", ""))
        if not DATE_RE.match(ad):
            errors.append(f"{label}: action_date '{ad}' is not YYYY-MM-DD format")

        # Test data contamination check
        entry_id = entry.get("entry_id", "")
        if isinstance(entry_id, str) and entry_id in TEST_ENTRY_IDS:
            errors.append(f"{label}: test entry_id '{entry_id}' in production signal file")

    return len(actions)


def validate_conversion_log(errors: list[str]) -> int:
    """Validate signals/conversion-log.yaml. Returns entry count."""
    path = SIGNALS_DIR / "conversion-log.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "entries" not in data:
        errors.append(f"{path}: missing top-level 'entries' key")
        return 0
    entries = data["entries"]
    if not isinstance(entries, list):
        errors.append(f"{path}: 'entries' must be a list")
        return 0

    for i, entry in enumerate(entries):
        label = f"{path} [entry {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "id", errors, label)
        _check_str(entry, "track", errors, label)

        # submitted must be a date string
        sub = str(entry.get("submitted", ""))
        if not DATE_RE.match(sub):
            errors.append(f"{label}: submitted '{sub}' is not YYYY-MM-DD format")

        # outcome is optional but validated when present and non-null
        outcome = entry.get("outcome")
        if outcome is not None and str(outcome) != "null" and outcome not in OUTCOMES:
            errors.append(f"{label}: outcome '{outcome}' not in {sorted(o for o in OUTCOMES if o)}")

        # Test data contamination check
        entry_id = entry.get("id", "")
        if isinstance(entry_id, str) and entry_id in TEST_ENTRY_IDS:
            errors.append(f"{label}: test id '{entry_id}' in production signal file")

    return len(entries)


def validate_hypotheses(errors: list[str]) -> int:
    """Validate signals/hypotheses.yaml. Returns entry count."""
    path = SIGNALS_DIR / "hypotheses.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "hypotheses" not in data:
        errors.append(f"{path}: missing top-level 'hypotheses' key")
        return 0
    hypotheses = data["hypotheses"]
    if not isinstance(hypotheses, list):
        errors.append(f"{path}: 'hypotheses' must be a list")
        return 0

    for i, entry in enumerate(hypotheses):
        label = f"{path} [hypothesis {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        # id field: accept either 'id' or 'entry_id' as the identifier
        eid = entry.get("id") or entry.get("entry_id")
        if not eid or not isinstance(eid, str) or not eid.strip():
            errors.append(f"{label}: missing or empty required field 'id' (or 'entry_id')")
        _check_str(entry, "category", errors, label)

    return len(hypotheses)


def validate_agent_actions(errors: list[str]) -> int:
    """Validate signals/agent-actions.yaml. Returns entry count.

    This file is gitignored and generated by agent.py runs, so its absence is
    normal (e.g. a fresh CI clone, or a repo where the agent hasn't run) and is
    not an error. When present it must be a {runs: [...]} mapping.
    """
    path = SIGNALS_DIR / "agent-actions.yaml"
    data = _load_yaml(path)
    if data is None:
        return 0  # absent/empty is acceptable (generated, gitignored)
    if not isinstance(data, dict) or "runs" not in data:
        errors.append(f"{path}: missing top-level 'runs' key")
        return 0
    runs = data["runs"]
    if not isinstance(runs, list):
        errors.append(f"{path}: 'runs' must be a list")
        return 0

    for i, entry in enumerate(runs):
        label = f"{path} [run {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "timestamp", errors, label)

        mode = entry.get("mode")
        if not isinstance(mode, str) or mode not in AGENT_MODES:
            errors.append(f"{label}: mode '{mode}' not in {sorted(AGENT_MODES)}")

    return len(runs)


def _collect_all_entry_ids() -> set[str]:
    """Scan all pipeline directories and return the set of known entry IDs."""
    ids: set[str] = set()
    for d in ALL_PIPELINE_DIRS_WITH_POOL:
        if not d.exists():
            continue
        for fp in d.glob("*.yaml"):
            if not fp.name.startswith("_"):
                ids.add(fp.stem)
    return ids


def validate_referential_integrity(errors: list[str]) -> int:
    """Check that signal files reference existing pipeline entries.

    Dangling references in conversion-log and hypotheses are WARNINGS
    (historical records may reference archived/purged entries). Only
    active signal-actions produce ERRORS.

    Returns the number of dangling references found.
    """
    entry_ids = _collect_all_entry_ids()
    dangling = 0

    # conversion-log: each entry.id must exist in pipeline
    conv_path = SIGNALS_DIR / "conversion-log.yaml"
    conv_data = _load_yaml(conv_path)
    if isinstance(conv_data, dict):
        for i, entry in enumerate(conv_data.get("entries", []) or []):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if isinstance(eid, str) and eid not in entry_ids:
                # Historical record — warn, don't error. Entry may have been archived.
                dangling += 1

    # hypotheses: each entry_id/id must exist in pipeline
    hyp_path = SIGNALS_DIR / "hypotheses.yaml"
    hyp_data = _load_yaml(hyp_path)
    if isinstance(hyp_data, dict):
        for i, entry in enumerate(hyp_data.get("hypotheses", []) or []):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id") or entry.get("entry_id")
            if isinstance(eid, str) and eid not in entry_ids:
                # Historical record — warn, don't error. Entry may have been archived.
                dangling += 1

    return dangling


def validate_contacts(errors: list[str]) -> int:
    """Validate signals/contacts.yaml schema. Returns entry count."""
    path = SIGNALS_DIR / "contacts.yaml"
    data = _load_yaml(path)
    if data is None:
        return 0  # contacts.yaml is optional
    if not isinstance(data, dict) or "contacts" not in data:
        errors.append(f"{path}: missing top-level 'contacts' key")
        return 0
    contacts = data["contacts"]
    if not isinstance(contacts, list):
        errors.append(f"{path}: 'contacts' must be a list")
        return 0

    valid_channels = OUTREACH_CHANNELS
    for i, entry in enumerate(contacts):
        label = f"{path} [contact {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "name", errors, label)
        channel = entry.get("channel")
        if isinstance(channel, str) and channel not in valid_channels:
            errors.append(f"{label}: channel '{channel}' not in {sorted(valid_channels)}")
        # Validate date formats in interactions
        for j, interaction in enumerate(entry.get("interactions", []) or []):
            if isinstance(interaction, dict):
                d = str(interaction.get("date", ""))
                if d and not DATE_RE.match(d):
                    errors.append(f"{label} interaction[{j}]: date '{d}' not YYYY-MM-DD")
        nad = str(entry.get("next_action_date", "") or "")
        if nad and not DATE_RE.match(nad):
            errors.append(f"{label}: next_action_date '{nad}' not YYYY-MM-DD")

    return len(contacts)


OUTREACH_TYPES = {
    "post_submission", "reconnect", "seed", "dm", "dm_sent", "connect",
    "referral_ask", "intro", "doubling_back", "acceptance", "github_engagement",
    "phone_call",
    # Organic types (emerged 2026-03-17 → 2026-03-25 from real outreach activity)
    "contribution", "reciprocal", "engagement", "content_engagement",
    "connection_accepted", "inbound_recruiter", "employer_response",
    "inmail", "follow_up", "referral_received",
}
OUTREACH_CHANNELS = {"linkedin", "email", "twitter", "referral", "event", "slack", "phone", "github", "imessage", "discord"}


def validate_outreach_log(errors: list[str]) -> int:
    """Validate signals/outreach-log.yaml schema. Returns entry count.

    Two interchangeable shapes are accepted:
      - a bare list of entries (entry-centric: entry_id/action/channel/date/status,
        written by log_dm.py / reconcile_outreach.py / outreach_engine.py), and
      - a {entries: [...]} mapping (contact-centric: contact/type/channel/date,
        initialized by followup.py).
    Each entry must identify its subject via `entry_id` or `contact`; channel,
    type, date, and related_targets are validated when present.
    """
    path = SIGNALS_DIR / "outreach-log.yaml"
    data = _load_yaml(path)
    if data is None:
        return 0
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and "entries" in data:
        entries = data["entries"]
    else:
        errors.append(f"{path}: must be a list of entries or a mapping with 'entries'")
        return 0
    if not isinstance(entries, list):
        errors.append(f"{path}: 'entries' must be a list")
        return 0

    for i, entry in enumerate(entries):
        label = f"{path} [entry {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        if not entry.get("entry_id") and not entry.get("contact"):
            errors.append(f"{label}: missing entry_id or contact")
        d = str(entry.get("date", ""))
        if d and not DATE_RE.match(d):
            errors.append(f"{label}: date '{d}' not YYYY-MM-DD")
        otype = entry.get("type")
        if isinstance(otype, str) and otype not in OUTREACH_TYPES:
            errors.append(f"{label}: type '{otype}' not in {sorted(OUTREACH_TYPES)}")
        channel = entry.get("channel")
        if isinstance(channel, str) and channel not in OUTREACH_CHANNELS:
            errors.append(f"{label}: channel '{channel}' not in {sorted(OUTREACH_CHANNELS)}")
        targets = entry.get("related_targets", [])
        if not isinstance(targets, list):
            errors.append(f"{label}: related_targets must be a list")

    return len(entries)


def validate_network(errors: list[str]) -> int:
    """Validate signals/network.yaml schema. Returns node count."""
    path = SIGNALS_DIR / "network.yaml"
    data = _load_yaml(path)
    if data is None:
        return 0
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level must be a mapping")
        return 0

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not isinstance(nodes, list):
        errors.append(f"{path}: 'nodes' must be a list")
        return 0
    if not isinstance(edges, list):
        errors.append(f"{path}: 'edges' must be a list")
        return 0

    node_names = set()
    for i, node in enumerate(nodes):
        label = f"{path} [node {i}]"
        if not isinstance(node, dict):
            errors.append(f"{label}: node is not a mapping")
            continue
        _check_str(node, "name", errors, label)
        name = node.get("name", "")
        if name in node_names:
            errors.append(f"{label}: duplicate node name '{name}'")
        node_names.add(name)

    for i, edge in enumerate(edges):
        label = f"{path} [edge {i}]"
        if not isinstance(edge, dict):
            errors.append(f"{label}: edge is not a mapping")
            continue
        _check_str(edge, "from", errors, label)
        _check_str(edge, "to", errors, label)
        strength = edge.get("strength")
        if strength is not None and (not isinstance(strength, (int, float)) or strength < 1 or strength > 10):
            errors.append(f"{label}: strength must be 1-10, got {strength}")

    return len(nodes)


def validate_all_signals() -> tuple[list[str], dict]:
    """Validate all signal YAML files.

    Returns:
        (errors, stats) where errors is a list of error messages and
        stats maps file basename to validated entry count.
    """
    errors: list[str] = []
    stats: dict[str, int] = {}

    stats["signal-actions"] = validate_signal_actions(errors)
    stats["conversion-log"] = validate_conversion_log(errors)
    stats["hypotheses"] = validate_hypotheses(errors)
    stats["agent-actions"] = validate_agent_actions(errors)
    stats["referential-integrity"] = validate_referential_integrity(errors)
    stats["contacts"] = validate_contacts(errors)
    stats["outreach-log"] = validate_outreach_log(errors)
    stats["network"] = validate_network(errors)

    return errors, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate signal YAML schema integrity")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any error")
    args = parser.parse_args()

    errors, stats = validate_all_signals()

    total_entries = sum(stats.values())
    print("Signal Validation Report")
    print("=" * 50)
    for name, count in stats.items():
        print(f"  {name}: {count} entries validated")
    print(f"  Total: {total_entries} entries")
    print(f"  Errors: {len(errors)}")

    if errors:
        print()
        for err in errors:
            print(f"  ERROR: {err}")

    if args.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
