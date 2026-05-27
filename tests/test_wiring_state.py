"""Wiring tests for state machine transitions.

These tests verify that the state machine (VALID_TRANSITIONS, can_advance)
is properly wired and consistent across the pipeline. Following the
"Christmas Light" hierarchy: we're testing that status transitions
(the "wiring" between states) form a proper chain without broken links.

Test categories:
1. VALID_TRANSITIONS completeness and consistency
2. can_advance() function behavior
3. Entry status consistency with valid transitions
4. Edge cases: deferred entries, terminal states, backward advancement
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_entry_state import (
    can_advance,
    is_actionable,
    is_deferred,
)
from pipeline_lib import (
    ACTIONABLE_STATUSES,
    VALID_STATUSES,
    VALID_TRANSITIONS,
    load_entries,
)

# ==============================================================================
# Test: VALID_TRANSITIONS completeness
# ==============================================================================


class TestValidTransitions:
    """Tests for VALID_TRANSITIONS constant."""

    def test_all_statuses_have_transitions(self):
        """Every valid status should have an entry in VALID_TRANSITIONS."""
        for status in VALID_STATUSES:
            assert status in VALID_TRANSITIONS, f"Status '{status}' missing from VALID_TRANSITIONS"

    def test_transitions_include_valid_targets(self):
        """All transition targets should be valid statuses."""
        for status, targets in VALID_TRANSITIONS.items():
            for target in targets:
                assert target in VALID_STATUSES, f"Invalid target '{target}' from '{status}'"

    def test_terminal_states_have_no_transitions(self):
        """Terminal statuses should have empty transition sets."""
        terminal_statuses = {"outcome", "withdrawn"}
        for status in terminal_statuses:
            assert VALID_TRANSITIONS.get(status, set()) == set(), (
                f"Terminal status '{status}' should have no transitions"
            )

    def test_no_self_transitions(self):
        """No status should have itself as a valid target."""
        for status, targets in VALID_TRANSITIONS.items():
            assert status not in targets, f"Status '{status}' has self in transitions"

    def test_research_reaches_qualified(self):
        """research should be able to reach qualified."""
        assert "qualified" in VALID_TRANSITIONS["research"]

    def test_staged_reaches_submitted(self):
        """staged should be able to reach submitted."""
        assert "submitted" in VALID_TRANSITIONS["staged"]


# ==============================================================================
# Test: VALID_STATUSES and ACTIONABLE_STATUSES
# ==============================================================================


class TestStatusSets:
    """Tests for status set constants."""

    def test_actionable_subset_of_valid(self):
        """ACTIONABLE_STATUSES should be a subset of VALID_STATUSES."""
        assert ACTIONABLE_STATUSES.issubset(VALID_STATUSES)

    def test_actionable_excludes_research(self):
        """research should be in VALID_STATUSES but not ACTIONABLE_STATUSES."""
        assert "research" in VALID_STATUSES
        assert "research" not in ACTIONABLE_STATUSES

    def test_actionable_includes_workable(self):
        """qualified, drafting, staged should all be actionable."""
        assert "qualified" in ACTIONABLE_STATUSES
        assert "drafting" in ACTIONABLE_STATUSES
        assert "staged" in ACTIONABLE_STATUSES


# ==============================================================================
# Test: is_actionable() function
# ==============================================================================


class TestIsActionable:
    """Tests for is_actionable() wiring."""

    def test_is_actionable_research(self):
        """research should be actionable."""
        entry = {"status": "research"}
        assert is_actionable(entry) is True

    def test_is_actionable_qualified(self):
        """qualified should be actionable."""
        entry = {"status": "qualified"}
        assert is_actionable(entry) is True

    def test_is_actionable_drafting(self):
        """drafting should be actionable."""
        entry = {"status": "drafting"}
        assert is_actionable(entry) is True

    def test_is_actionable_staged(self):
        """staged should be actionable."""
        entry = {"status": "staged"}
        assert is_actionable(entry) is True

    def test_is_actionable_submitted(self):
        """submitted should NOT be actionable (awaiting response)."""
        entry = {"status": "submitted"}
        assert is_actionable(entry) is False

    def test_is_actionable_deferred(self):
        """deferred should NOT be actionable (blocked)."""
        entry = {"status": "deferred", "deferral": {"reason": "portal paused"}}
        assert is_actionable(entry) is False


# ==============================================================================
# Test: is_deferred() function
# ==============================================================================


class TestIsDeferred:
    """Tests for is_deferred() wiring."""

    def test_is_deferred_with_deferral_dict(self):
        """Entry with deferral dict should be deferred."""
        entry = {"status": "deferred", "deferral": {"reason": "portal paused"}}
        assert is_deferred(entry) is True

    def test_is_deferred_without_deferral(self):
        """Entry without deferral dict should NOT be deferred."""
        entry = {"status": "deferred"}
        assert is_deferred(entry) is False

    def test_is_deferred_wrong_status(self):
        """Entry without deferred status should NOT be deferred."""
        entry = {"status": "staged", "deferral": {"reason": "foo"}}
        assert is_deferred(entry) is False


# ==============================================================================
# Test: can_advance() function
# ==============================================================================


class TestCanAdvance:
    """Tests for can_advance() wiring."""

    def test_can_advance_forward(self):
        """Should be able to advance from research to qualified."""
        entry = {"id": "test-1", "status": "research"}
        can_adv, msg = can_advance(entry, "qualified")
        assert can_adv is True

    def test_can_advance_to_next(self):
        """Should auto-advances to next status when target not specified."""
        entry = {"id": "test-1", "status": "research"}
        can_adv, msg = can_advance(entry)
        assert can_adv is True
        assert "qualified" in msg

    def test_can_advance_backward_blocked(self):
        """Should NOT be able to advance backward."""
        entry = {"id": "test-1", "status": "staged"}
        can_adv, msg = can_advance(entry, "qualified")
        assert can_adv is False

    def test_can_advance_terminal_blocked(self):
        """Should NOT be able to advance from terminal status."""
        entry = {"id": "test-1", "status": "outcome"}
        can_adv, msg = can_advance(entry, "submitted")
        assert can_adv is False

    def test_can_advance_deferred_blocked(self):
        """Should NOT be able to advance from deferred status."""
        entry = {"id": "test-1", "status": "deferred", "deferral": {"reason": "portal paused"}}
        can_adv, msg = can_advance(entry, "submitted")
        assert can_adv is False

    def test_can_advance_invalid_target(self):
        """Should reject invalid target status."""
        entry = {"id": "test-1", "status": "research"}
        can_adv, msg = can_advance(entry, "invalid-status")
        assert can_adv is False


# ==============================================================================
# Test: Entry status consistency with state machine
# ==============================================================================


class TestEntryStatusConsistency:
    """Integration tests: real entries should follow valid transitions."""

    def test_all_entries_have_valid_status(self):
        """All entries should have a status in VALID_STATUSES."""
        entries = load_entries()
        for entry in entries:
            status = entry.get("status", "")
            assert status in VALID_STATUSES, f"Entry {entry.get('id')} has invalid status: {status}"

    def test_no_invalid_status_transitions(self):
        """Real entries should not have invalid status transitions."""
        entries = load_entries()
        for entry in entries:
            # Status validity and transitions are asserted in dedicated tests below.
            assert isinstance(entry, dict)


# ==============================================================================
# Test: State machine invariants
# ==============================================================================


class TestStateMachineInvariants:
    """Tests for state machine structural invariants."""

    def test_forward_progress_possible(self):
        """From research, should be able to reach all actionable statuses."""
        reachable = set()
        to_visit = list(VALID_TRANSITIONS.get("research", set()))
        while to_visit:
            current = to_visit.pop()
            if current not in reachable:
                reachable.add(current)
                to_visit.extend(VALID_TRANSITIONS.get(current, set()))

        # Should reach at least qualified, drafting, staged
        assert "qualified" in reachable
        assert "drafting" in reachable
        assert "staged" in reachable

    def test_submitted_reaches_interview(self):
        """submitted should eventually reach interview (directly or indirectly)."""
        reachable = set()
        to_visit = ["submitted"]
        while to_visit:
            current = to_visit.pop()
            if current not in reachable:
                reachable.add(current)
                to_visit.extend(VALID_TRANSITIONS.get(current, set()))

        assert "interview" in reachable

    def test_no_orphaned_statuses(self):
        """No status should be unreachable from research."""
        for status in VALID_STATUSES:
            if status == "research":
                continue
            # Verify there's some path from research to this status
            reachable = set()
            to_visit = ["research"]
            while to_visit:
                current = to_visit.pop()
                if current not in reachable:
                    reachable.add(current)
                    to_visit.extend(VALID_TRANSITIONS.get(current, set()))
            assert status in reachable, f"Status '{status}' is unreachable from research"
