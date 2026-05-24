"""Direct tests for scripts/score_pillar_dimensions.py (three-pillar dims)."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_pillar_dimensions as pd


def _iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# --- studio_alignment (Jobs) ---

def test_studio_alignment_high_for_aligned_role():
    entry = {
        "track": "job",
        "name": "AI platform research engineer",
        "target": {"organization": "Anthropic"},
        "fit": {"identity_position": "creative-technologist"},
    }
    # base 5 + position(+2) + keywords(+2 cap) + studio-tier org(+1) = 10
    assert pd.score_studio_alignment(entry) == 10


def test_studio_alignment_neutral_for_unaligned_role():
    entry = {
        "track": "job",
        "name": "Staff Accountant",
        "target": {"organization": "Local Bakery"},
        "fit": {"identity_position": "founder-operator"},
    }
    assert pd.score_studio_alignment(entry) == 5


def test_studio_alignment_explain_returns_reason():
    val, reason = pd.score_studio_alignment({"name": "ml infrastructure"}, explain=True)
    assert 1 <= val <= 10
    assert isinstance(reason, str) and reason


# --- remote_flexibility (Jobs) ---

def test_remote_flexibility_mapping():
    cases = {
        "remote-global": 10,
        "us-remote": 8,
        "hybrid": 6,
        "us-onsite": 3,
        "international": 2,
    }
    for loc_class, expected in cases.items():
        entry = {"target": {"location_class": loc_class}}
        assert pd.score_remote_flexibility(entry) == expected, loc_class


def test_remote_flexibility_unknown_is_neutral():
    assert pd.score_remote_flexibility({"target": {"location_class": "unknown"}}) == 5


def test_remote_flexibility_falls_back_to_location_text():
    entry = {"target": {"location_class": "", "location": "Fully Remote (US)"}}
    assert pd.score_remote_flexibility(entry) == 8


# --- narrative_fit (Grants) ---

def test_narrative_fit_rewards_blocks_and_framing():
    rich = {
        "submission": {"blocks_used": {"a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1},
                       "variant_ids": {"cover_letter": "x"}},
        "fit": {"framing": "A long, specific framing well beyond thirty characters."},
    }
    bare = {"submission": {}, "fit": {}}
    assert pd.score_narrative_fit(rich) > pd.score_narrative_fit(bare)
    assert pd.score_narrative_fit(bare) == 4  # base only


# --- prestige_multiplier (Grants) ---

def test_prestige_multiplier_uses_prestige_list():
    entry = {"target": {"organization": "Creative Capital"}}
    assert pd.score_prestige_multiplier(entry) == 10


def test_prestige_multiplier_unknown_org_neutral():
    assert pd.score_prestige_multiplier({"target": {"organization": "Obscure Foundation"}}) == 5


# --- cycle_urgency (Grants) ---

def test_cycle_urgency_rolling_is_low():
    assert pd.score_cycle_urgency({"deadline": {"type": "rolling"}}) == 3


def test_cycle_urgency_imminent_is_high():
    assert pd.score_cycle_urgency({"deadline": {"type": "hard", "date": _iso(5)}}) == 9


def test_cycle_urgency_far_off_is_low():
    assert pd.score_cycle_urgency({"deadline": {"type": "hard", "date": _iso(120)}}) == 4


def test_cycle_urgency_past_deadline():
    assert pd.score_cycle_urgency({"deadline": {"type": "hard", "date": _iso(-3)}}) == 1


# --- recurring_potential (Consulting) ---

def test_recurring_potential_rewards_recurring_signals():
    entry = {"track": "consulting", "name": "Monthly retainer advisory partnership",
             "target": {"organization": "Acme"}}
    assert pd.score_recurring_potential(entry) >= 8


def test_recurring_potential_penalizes_one_off():
    entry = {"track": "consulting", "name": "One-time workshop", "target": {}}
    base_consulting = pd.score_recurring_potential({"track": "consulting", "target": {}})
    assert pd.score_recurring_potential(entry) < base_consulting


# --- client_fit (Consulting) ---

def test_client_fit_strong_network_and_studio_org():
    entry = {
        "track": "consulting",
        "target": {"organization": "Anthropic"},
        "network": {"relationship_strength": "strong"},
        "fit": {"identity_position": "creative-technologist"},
    }
    # base 5 + strong(+2) + studio-tier org(+1) + aligned position(+1) = 9
    assert pd.score_client_fit(entry) == 9


def test_client_fit_cold_relationship_below_base():
    entry = {"target": {}, "network": {"relationship_strength": "cold"}}
    assert pd.score_client_fit(entry) == 4


def test_all_scorers_return_in_range_for_empty_entry():
    empty = {}
    for fn in (pd.score_studio_alignment, pd.score_remote_flexibility, pd.score_narrative_fit,
               pd.score_prestige_multiplier, pd.score_cycle_urgency, pd.score_recurring_potential,
               pd.score_client_fit):
        assert 1 <= fn(empty) <= 10, fn.__name__
