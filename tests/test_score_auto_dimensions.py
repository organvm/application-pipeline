"""Direct tests for scripts/score_auto_dimensions.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_auto_dimensions


def _entry(**overrides):
    base = {
        "track": "grant",
        "deadline": {"type": "rolling"},
        "amount": {"value": 0},
        "target": {"portal": "email", "organization": "Creative Capital"},
        "submission": {"blocks_used": {}},
        "fit": {},
    }
    base.update(overrides)
    return base


def test_score_deadline_feasibility_rolling():
    score = score_auto_dimensions.score_deadline_feasibility(_entry())
    assert score == 9


def test_score_financial_alignment_respects_limits():
    score = score_auto_dimensions.score_financial_alignment(
        _entry(amount={"value": 20000}),
        snap_limit=20352,
        medicaid_limit=21597,
        essential_plan_limit=39125,
    )
    assert score == 9


def test_differentiation_boost_thresholds():
    score_auto_dimensions._DIFF_COMPOSITE = 8.6
    boost, comp = score_auto_dimensions._get_differentiation_boost()
    assert boost == 2
    assert comp == 8.6


def test_score_strategic_value_prestige_match():
    score = score_auto_dimensions.score_strategic_value(_entry())
    assert score == 10


def test_effort_base_academic_fallback():
    """Academic uses the residency/fellowship-kin effort fallback of 5."""
    assert score_auto_dimensions._get_effort_base_from_market("academic") == 5


def test_effort_base_unknown_track_degrades():
    """A genuinely unknown track degrades to the neutral default of 5, not an error."""
    assert score_auto_dimensions._get_effort_base_from_market("definitely-not-a-track") == 5
