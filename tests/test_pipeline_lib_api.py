#!/usr/bin/env python3
"""API stability test for pipeline_lib.py.

Ensures the public API surface of pipeline_lib doesn't accidentally break.
Any function or constant removal should be a deliberate, reviewed change.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


# --- Public functions that must exist ---

REQUIRED_FUNCTIONS = [
    "atomic_write",
    "check_company_cap",
    "compute_freshness_score",
    "count_chars",
    "count_words",
    "days_until",
    "detect_entry_portal",
    "detect_portal",
    "ensure_yaml_field",
    "get_deadline",
    "get_effort",
    "get_mode_thresholds",
    "get_pipeline_mode",
    "get_score",
    "get_tier",
    "load_block",
    "load_block_frontmatter",
    "load_block_index",
    "load_entries",
    "load_entry_by_id",
    "load_legacy_script",
    "load_market_intelligence",
    "load_profile",
    "load_submit_config",
    "load_variant",
    "parse_date",
    "resolve_cover_letter",
    "resolve_resume",
    "strip_markdown",
    "update_last_touched",
    "update_yaml_field",
]

# --- Public constants that must exist ---

REQUIRED_CONSTANTS = [
    "ACTIONABLE_STATUSES",
    "ALL_PIPELINE_DIRS",
    "ALL_PIPELINE_DIRS_WITH_POOL",
    "BLOCKS_DIR",
    "COMPANY_CAP",
    "CURRENT_BATCH",
    "DIMENSION_ORDER",
    "EFFORT_MINUTES",
    "MATERIALS_DIR",
    "PIPELINE_DIR_ACTIVE",
    "PIPELINE_DIR_CLOSED",
    "PIPELINE_DIR_RESEARCH_POOL",
    "PIPELINE_DIR_SUBMITTED",
    "PROFILES_DIR",
    "PROFILE_ID_MAP",
    "REPO_ROOT",
    "SIGNALS_DIR",
    "STATUS_ORDER",
    "VALID_DIMENSIONS",
    "VALID_STATUSES",
    "VALID_TRACKS",
    "VALID_TRANSITIONS",
    "VARIANTS_DIR",
]


def test_all_public_functions_exist():
    """Every required public function must be importable from pipeline_lib."""
    import pipeline_lib

    missing = []
    for name in REQUIRED_FUNCTIONS:
        if not hasattr(pipeline_lib, name):
            missing.append(name)

    assert not missing, f"Missing public functions from pipeline_lib: {missing}"


def test_all_public_constants_exist():
    """Every required public constant must be importable from pipeline_lib."""
    import pipeline_lib

    missing = []
    for name in REQUIRED_CONSTANTS:
        if not hasattr(pipeline_lib, name):
            missing.append(name)

    assert not missing, f"Missing public constants from pipeline_lib: {missing}"


def test_function_signatures_stable():
    """Key functions must accept their documented parameters."""
    import inspect

    import pipeline_lib

    # load_entries must accept dirs and include_filepath
    sig = inspect.signature(pipeline_lib.load_entries)
    params = list(sig.parameters.keys())
    assert "dirs" in params or len(params) >= 1, "load_entries must accept dirs parameter"

    # atomic_write must accept filepath and content
    sig = inspect.signature(pipeline_lib.atomic_write)
    params = list(sig.parameters.keys())
    assert len(params) >= 2, "atomic_write must accept filepath and content"

    # update_yaml_field must accept content, field, new_value
    sig = inspect.signature(pipeline_lib.update_yaml_field)
    params = list(sig.parameters.keys())
    assert len(params) >= 3, "update_yaml_field must accept content, field, new_value"


def test_valid_transitions_complete():
    """VALID_TRANSITIONS must cover all actionable statuses."""
    import pipeline_lib

    for status in pipeline_lib.ACTIONABLE_STATUSES:
        assert status in pipeline_lib.VALID_TRANSITIONS, (
            f"ACTIONABLE_STATUSES contains '{status}' but VALID_TRANSITIONS lacks it"
        )


def test_dimension_order_matches_valid_dimensions():
    """DIMENSION_ORDER (9 core) is a subset of VALID_DIMENSIONS.

    Three-pillar model: VALID_DIMENSIONS = the 9 core (DIMENSION_ORDER) plus the
    7 pillar-specific dimensions, so DIMENSION_ORDER is a strict subset.
    """
    import pipeline_lib

    dim_set = set(pipeline_lib.DIMENSION_ORDER)
    valid_set = set(pipeline_lib.VALID_DIMENSIONS)
    assert dim_set <= valid_set, f"DIMENSION_ORDER has dims not in VALID_DIMENSIONS: {dim_set - valid_set}"
    assert set(pipeline_lib.PILLAR_DIMENSIONS) <= valid_set
    assert valid_set == dim_set | set(pipeline_lib.PILLAR_DIMENSIONS)
