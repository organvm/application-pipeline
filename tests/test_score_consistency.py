"""Tests that score thresholds are consistent between code and config.

Validates that scoring-rubric.yaml, score.py constants, and agent-rules.yaml
agree on thresholds, weights, and dimensions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = ROOT / "strategy" / "scoring-rubric.yaml"
AGENT_RULES_PATH = ROOT / "strategy" / "agent-rules.yaml"

EXPECTED_DIMENSIONS = [
    "mission_alignment",
    "evidence_match",
    "track_record_fit",
    "network_proximity",
    "strategic_value",
    "financial_alignment",
    "effort_to_value",
    "deadline_feasibility",
    "portal_friction",
]


def _load_rubric() -> dict:
    with open(RUBRIC_PATH) as f:
        return yaml.safe_load(f)


def _load_agent_rules() -> dict:
    with open(AGENT_RULES_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Test 1: score.py constants match scoring-rubric.yaml
# ---------------------------------------------------------------------------


def test_score_constants_match_rubric():
    """Code-level thresholds loaded from rubric must match YAML source of truth."""
    from score import (
        AUTO_ADVANCE_DRAFTING,
        AUTO_QUALIFY_MIN,
        WEIGHTS,
        WEIGHTS_JOB,
    )

    rubric = _load_rubric()
    thresholds = rubric["thresholds"]

    # auto_qualify_min
    assert AUTO_QUALIFY_MIN == thresholds["auto_qualify_min"], (
        f"AUTO_QUALIFY_MIN={AUTO_QUALIFY_MIN} != rubric {thresholds['auto_qualify_min']}"
    )

    # auto_advance_to_drafting
    assert AUTO_ADVANCE_DRAFTING == thresholds["auto_advance_to_drafting"], (
        f"AUTO_ADVANCE_DRAFTING={AUTO_ADVANCE_DRAFTING} != rubric {thresholds['auto_advance_to_drafting']}"
    )

    # Generic weights sum to 1.0
    rubric_weights = rubric["weights"]
    assert abs(sum(rubric_weights.values()) - 1.0) < 1e-9, (
        f"Rubric generic weights sum to {sum(rubric_weights.values())}"
    )
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, (
        f"Code WEIGHTS sum to {sum(WEIGHTS.values())}"
    )

    # Job weights sum to 1.0
    rubric_weights_job = rubric["weights_job"]
    assert abs(sum(rubric_weights_job.values()) - 1.0) < 1e-9, (
        f"Rubric job weights sum to {sum(rubric_weights_job.values())}"
    )
    assert abs(sum(WEIGHTS_JOB.values()) - 1.0) < 1e-9, (
        f"Code WEIGHTS_JOB sum to {sum(WEIGHTS_JOB.values())}"
    )

    # Individual weight values match between code and rubric
    for dim, rubric_val in rubric_weights.items():
        assert dim in WEIGHTS, f"Rubric dimension '{dim}' missing from WEIGHTS"
        assert abs(WEIGHTS[dim] - rubric_val) < 1e-9, (
            f"WEIGHTS['{dim}']={WEIGHTS[dim]} != rubric {rubric_val}"
        )

    for dim, rubric_val in rubric_weights_job.items():
        assert dim in WEIGHTS_JOB, f"Rubric dimension '{dim}' missing from WEIGHTS_JOB"
        assert abs(WEIGHTS_JOB[dim] - rubric_val) < 1e-9, (
            f"WEIGHTS_JOB['{dim}']={WEIGHTS_JOB[dim]} != rubric {rubric_val}"
        )


# ---------------------------------------------------------------------------
# Test 2: agent-rules.yaml thresholds are consistent with scoring-rubric.yaml
# ---------------------------------------------------------------------------


def test_agent_rules_match_rubric():
    """Agent advance thresholds must be consistent with rubric thresholds."""
    rubric = _load_rubric()
    agent_data = _load_agent_rules()
    rules = agent_data["rules"]
    thresholds = rubric["thresholds"]

    # Agent research->qualified threshold should match rubric auto_qualify_min
    research_threshold = rules["advance_research_to_qualified"]["threshold"]
    assert research_threshold == thresholds["auto_qualify_min"], (
        f"Agent research->qualified threshold ({research_threshold}) "
        f"!= rubric auto_qualify_min ({thresholds['auto_qualify_min']})"
    )

    # Agent qualified->drafting threshold should match rubric auto_advance_to_drafting
    drafting_threshold = rules["advance_qualified_to_drafting"]["threshold"]
    assert drafting_threshold == thresholds["auto_advance_to_drafting"], (
        f"Agent qualified->drafting threshold ({drafting_threshold}) "
        f"!= rubric auto_advance_to_drafting ({thresholds['auto_advance_to_drafting']})"
    )

    # Agent drafting->staged min_score should not exceed auto_advance_to_drafting
    staged_min_score = rules["advance_drafting_to_staged"]["min_score"]
    assert staged_min_score <= thresholds["auto_advance_to_drafting"], (
        f"Agent drafting->staged min_score ({staged_min_score}) "
        f"> rubric auto_advance_to_drafting ({thresholds['auto_advance_to_drafting']})"
    )

    # All agent thresholds should be within rubric score range
    score_min = thresholds["score_range_min"]
    score_max = thresholds["score_range_max"]
    for name, value in [
        ("research->qualified", research_threshold),
        ("qualified->drafting", drafting_threshold),
        ("drafting->staged min_score", staged_min_score),
    ]:
        assert score_min <= value <= score_max, (
            f"Agent threshold '{name}'={value} outside rubric range [{score_min}, {score_max}]"
        )


# ---------------------------------------------------------------------------
# Test 3: all 9 dimensions exist in both weight dicts in code
# ---------------------------------------------------------------------------


def test_weight_dimensions_match():
    """Code weight sets mirror the rubric and use only valid (pillar) dimensions.

    Three-pillar model: weights_job / weights_grant / weights (legacy) each use a
    pillar-specific SUBSET of VALID_DIMENSIONS, so we no longer require all 9 core
    dimensions in every set — only that code mirrors the rubric, uses known
    dimensions, and sums to 1.0.
    """
    from pipeline_lib import VALID_DIMENSIONS
    from score import WEIGHTS, WEIGHTS_JOB

    rubric = _load_rubric()

    # Code weight dicts must mirror the rubric YAML.
    assert set(WEIGHTS.keys()) == set(rubric["weights"].keys())
    assert set(WEIGHTS_JOB.keys()) == set(rubric["weights_job"].keys())

    # Only known dimensions, each set normalized to 1.0.
    for name, w in (("WEIGHTS", WEIGHTS), ("WEIGHTS_JOB", WEIGHTS_JOB)):
        unknown = set(w.keys()) - VALID_DIMENSIONS
        assert not unknown, f"{name} has unknown dimensions: {unknown}"
        assert abs(sum(w.values()) - 1.0) < 1e-9, f"{name} sums to {sum(w.values())}, not 1.0"

    # The 9 core dimensions remain valid dimensions in the three-pillar model.
    assert set(EXPECTED_DIMENSIONS) <= VALID_DIMENSIONS
