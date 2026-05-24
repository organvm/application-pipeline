#!/usr/bin/env python3
"""Score pipeline entries against the multi-dimensional rubric.

Auto-derives scores for deadline_feasibility, financial_alignment,
portal_friction, and effort_to_value from existing data. Computes
mission_alignment, evidence_match, and track_record_fit from structured
signals (profiles, blocks, portal fields, cross-pipeline history).
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import score_auto_dimensions as _auto_dimensions
import score_constants as _score_constants
import score_explain as _score_explain
import score_human_dimensions as _human_dimensions
import score_network as _score_network
import score_pillar_dimensions as _pillar_dimensions
import score_reachability as _score_reachability
import score_telemetry as _score_telemetry
import yaml
from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    DIMENSION_ORDER,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    PORTAL_SCORES_DEFAULT,
    STRATEGIC_BASE_DEFAULT,
    atomic_write,
    load_entry_by_id,
    update_last_touched,
    update_yaml_field,
)
from pipeline_lib import (
    load_entries as _load_entries_raw,
)
from pipeline_lib import (
    load_market_intelligence as _load_market_intelligence,
)

HIGH_PRESTIGE = _score_constants.HIGH_PRESTIGE
ROLE_FIT_TIERS = _score_constants.ROLE_FIT_TIERS
load_market_intelligence = _load_market_intelligence

# --- Scoring rubric loader ---

_RUBRIC_PATH = Path(__file__).resolve().parent.parent / "strategy" / "scoring-rubric.yaml"


def _load_rubric() -> dict:
    """Load scoring rubric from YAML, falling back to hardcoded defaults."""
    if _RUBRIC_PATH.exists():
        try:
            with open(_RUBRIC_PATH) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


_RUBRIC = _load_rubric()

# --- Dimension weights (must sum to 1.0)
# Loaded from strategy/scoring-rubric.yaml with hardcoded fallback.
_DEFAULT_WEIGHTS_GRANT = {
    "mission_alignment": 0.20,
    "narrative_fit": 0.18,
    "evidence_match": 0.15,
    "prestige_multiplier": 0.12,
    "cycle_urgency": 0.10,
    "network_proximity": 0.08,
    "track_record_fit": 0.07,
    "strategic_value": 0.05,
    "financial_alignment": 0.03,
    "effort_to_value": 0.02,
}
_DEFAULT_WEIGHTS_JOB = {
    "network_proximity": 0.22,
    "deadline_feasibility": 0.18,
    "evidence_match": 0.18,
    "mission_alignment": 0.13,
    "studio_alignment": 0.08,
    "remote_flexibility": 0.07,
    "strategic_value": 0.06,
    "effort_to_value": 0.04,
    "track_record_fit": 0.02,
    "financial_alignment": 0.01,
    "portal_friction": 0.01,
}
_DEFAULT_WEIGHTS_CONSULTING = {
    "network_proximity": 0.22,
    "recurring_potential": 0.18,
    "studio_alignment": 0.15,
    "client_fit": 0.12,
    "evidence_match": 0.10,
    "mission_alignment": 0.08,
    "strategic_value": 0.07,
    "effort_to_value": 0.05,
    "financial_alignment": 0.03,
}

# Load from rubric YAML with fallbacks
WEIGHTS = _RUBRIC.get("weights", _DEFAULT_WEIGHTS_GRANT)
WEIGHTS_JOB = _RUBRIC.get("weights_job", _DEFAULT_WEIGHTS_JOB)
WEIGHTS_GRANT = _RUBRIC.get("weights_grant", _DEFAULT_WEIGHTS_GRANT)
WEIGHTS_CONSULTING = _RUBRIC.get("weights_consulting", _DEFAULT_WEIGHTS_CONSULTING)

# Pillar track mapping
_GRANT_TRACKS = {"grant", "residency", "fellowship", "prize", "writing", "emergency"}
_CONSULTING_TRACKS = {"consulting"}

# Validate weight dicts sum to 1.0
for _name, _w in [("WEIGHTS", WEIGHTS), ("WEIGHTS_JOB", WEIGHTS_JOB),
                   ("WEIGHTS_GRANT", WEIGHTS_GRANT), ("WEIGHTS_CONSULTING", WEIGHTS_CONSULTING)]:
    assert abs(sum(_w.values()) - 1.0) < 1e-9, f"{_name} sum to {sum(_w.values())}, not 1.0"

# Thresholds from rubric (with fallback)
_THRESHOLDS = _RUBRIC.get("thresholds", {})
AUTO_QUALIFY_MIN = _THRESHOLDS.get("auto_qualify_min", 7.0)
AUTO_ADVANCE_DRAFTING = _THRESHOLDS.get("auto_advance_to_drafting", 8.0)

# Benefits cliff thresholds (annual USD)
_CLIFFS = _RUBRIC.get("benefits_cliffs", {})
SNAP_LIMIT = _CLIFFS.get("snap_limit", 20352)
MEDICAID_LIMIT = _CLIFFS.get("medicaid_limit", 21597)
ESSENTIAL_PLAN_LIMIT = _CLIFFS.get("essential_plan_limit", 39125)

# Backward-compatible module-level aliases (default/fallback values).
# Callers that use the dynamic loaders (get_portal_scores(), get_strategic_base())
# will get market-intelligence-backed values. These constants exist only for
# callers that import PORTAL_SCORES / STRATEGIC_BASE by name.
PORTAL_SCORES = PORTAL_SCORES_DEFAULT
STRATEGIC_BASE = STRATEGIC_BASE_DEFAULT

TRACK_POSITION_AFFINITY = _human_dimensions.TRACK_POSITION_AFFINITY
POSITION_EXPECTED_ORGANS = _human_dimensions.POSITION_EXPECTED_ORGANS
CREDENTIALS = _human_dimensions.CREDENTIALS


def estimate_role_fit_from_title(entry: dict) -> dict[str, int]:
    return _human_dimensions.estimate_role_fit_from_title(entry)


def _ma_position_profile_match(entry: dict, profile: dict | None) -> tuple[int, str]:
    return _human_dimensions._ma_position_profile_match(entry, profile)


def _ma_track_position_affinity(entry: dict) -> tuple[int, str]:
    return _human_dimensions._ma_track_position_affinity(entry)


def _ma_organ_position_coherence(entry: dict) -> tuple[int, str]:
    return _human_dimensions._ma_organ_position_coherence(entry)


def _ma_framing_specialization(entry: dict) -> tuple[int, str]:
    return _human_dimensions._ma_framing_specialization(entry)


def _em_block_portal_coverage(entry: dict) -> tuple[int, str]:
    return _human_dimensions._em_block_portal_coverage(entry)


def _em_slot_name_alignment(entry: dict) -> tuple[int, str]:
    return _human_dimensions._em_slot_name_alignment(entry)


def _em_evidence_depth(entry: dict) -> tuple[int, str]:
    return _human_dimensions._em_evidence_depth(entry)


def _em_materials_readiness(entry: dict) -> tuple[int, str]:
    return _human_dimensions._em_materials_readiness(entry)


def _tr_credential_track_relevance(entry: dict) -> tuple[int, str]:
    return _human_dimensions._tr_credential_track_relevance(entry)


def _tr_track_experience(entry: dict, all_entries: list[dict]) -> tuple[int, str]:
    return _human_dimensions._tr_track_experience(entry, all_entries)


def _tr_position_depth(entry: dict) -> tuple[int, str]:
    return _human_dimensions._tr_position_depth(entry)


def _tr_differentiators_coverage(entry: dict, profile: dict | None) -> tuple[int, str]:
    return _human_dimensions._tr_differentiators_coverage(entry, profile)


def load_entries(entry_id: str | None = None, include_pool: bool = False) -> list[tuple[Path, dict]]:
    """Load pipeline entries as (filepath, data) tuples.

    If entry_id given, load only that one.
    If include_pool, also scan research_pool/ (for explicit --include-pool flag).

    Default (include_pool=False): loads active/ + submitted/ + closed/ only.
    Research pool entries are ONLY scored via --auto-qualify, which has its
    own dedicated loading logic in run_auto_qualify().
    """
    if entry_id:
        filepath, data = load_entry_by_id(entry_id)
        if filepath and data:
            return [(filepath, data)]
        return []

    dirs = ALL_PIPELINE_DIRS_WITH_POOL if include_pool else None
    entries = _load_entries_raw(dirs=dirs, include_filepath=True)
    return [(e.pop("_filepath"), e) for e in entries if "_filepath" in e]


def score_deadline_feasibility(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _auto_dimensions.score_deadline_feasibility(entry, explain=explain)


def score_financial_alignment(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _auto_dimensions.score_financial_alignment(
        entry,
        SNAP_LIMIT,
        MEDICAID_LIMIT,
        ESSENTIAL_PLAN_LIMIT,
        explain=explain,
    )


def score_portal_friction(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _auto_dimensions.score_portal_friction(entry, explain=explain)


def _get_effort_base_from_market(track: str) -> int:
    return _auto_dimensions._get_effort_base_from_market(track)


def score_effort_to_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _auto_dimensions.score_effort_to_value(entry, explain=explain)


def _get_differentiation_boost() -> tuple[int, float]:
    return _auto_dimensions._get_differentiation_boost()


def score_strategic_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _auto_dimensions.score_strategic_value(entry, explain=explain)


# --- Pillar-specific dimensions (three-pillar rubric) ---


def score_studio_alignment(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_studio_alignment(entry, explain=explain)


def score_remote_flexibility(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_remote_flexibility(entry, explain=explain)


def score_narrative_fit(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_narrative_fit(entry, explain=explain)


def score_prestige_multiplier(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_prestige_multiplier(entry, explain=explain)


def score_cycle_urgency(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_cycle_urgency(entry, explain=explain)


def score_recurring_potential(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_recurring_potential(entry, explain=explain)


def score_client_fit(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    return _pillar_dimensions.score_client_fit(entry, explain=explain)


# Maps each pillar dimension to its scorer (used by compute_dimensions).
_PILLAR_SCORERS = {
    "studio_alignment": score_studio_alignment,
    "remote_flexibility": score_remote_flexibility,
    "narrative_fit": score_narrative_fit,
    "prestige_multiplier": score_prestige_multiplier,
    "cycle_urgency": score_cycle_urgency,
    "recurring_potential": score_recurring_potential,
    "client_fit": score_client_fit,
}


def compute_human_dimensions(
    entry: dict,
    all_entries: list[dict] | None = None,
    explain: bool = False,
) -> dict[str, int] | tuple[dict[str, int], dict[str, str]]:
    return _human_dimensions.compute_human_dimensions(
        entry,
        all_entries=all_entries,
        explain=explain,
    )


# Keep backward-compatible alias for any external callers
estimate_human_dimensions = compute_human_dimensions


_NETWORK_DECAY = _score_network._NETWORK_DECAY


def _days_since(date_str: str | None) -> int | None:
    return _score_network._days_since(date_str)


def score_network_proximity(entry: dict, all_entries: list[dict] | None = None) -> int:
    return _score_network.score_network_proximity(entry, all_entries)


def _log_network_change(entry_id: str, old_network: int, new_network: int, filepath: Path):
    return _score_network._log_network_change(entry_id, old_network, new_network, filepath)


def compute_dimensions(entry: dict, all_entries: list[dict] | None = None) -> dict[str, int]:
    """Compute all dimension scores for an entry (9 core + 7 pillar).

    All dimensions are always recomputed from data. No human overrides.
    Signal-based dimensions replace the old gut-feel estimation. Pillar-specific
    dimensions are computed for every entry; compute_composite uses only those
    weighted for the entry's track.
    """
    dims = {}

    # Auto-derivable (always recompute)
    dims["deadline_feasibility"] = score_deadline_feasibility(entry)
    dims["financial_alignment"] = score_financial_alignment(entry)
    dims["portal_friction"] = score_portal_friction(entry)
    dims["effort_to_value"] = score_effort_to_value(entry)
    dims["strategic_value"] = score_strategic_value(entry)
    dims["network_proximity"] = score_network_proximity(entry, all_entries)

    # Signal-based (replaces estimate + override)
    human = compute_human_dimensions(entry, all_entries)
    dims.update(human)

    # Pillar-specific dimensions (three-pillar rubric). compute_composite only
    # consumes the ones weighted for the entry's track, but we compute all so
    # explain/diagnostics can surface them.
    for dim_name, scorer in _PILLAR_SCORERS.items():
        dims[dim_name] = scorer(entry)

    return dims


def applicant_density_adjustment(entry: dict) -> float:
    """Compute a score adjustment based on applicant density.

    Reads `target.applicant_density` from the entry (optional field).
    Values: "low" (<50), "medium" (50-500), "high" (500-2000), "extreme" (2000+).
    Also accepts an integer for exact applicant count.

    Returns a float adjustment: positive for low density, negative for high.
    The adjustment is small (±0.3 max) to avoid dominating the composite.
    """
    target = entry.get("target", {})
    if not isinstance(target, dict):
        return 0.0
    density = target.get("applicant_density")
    if density is None:
        return 0.0

    if isinstance(density, (int, float)):
        if density < 50:
            return 0.3
        elif density < 500:
            return 0.0
        elif density < 2000:
            return -0.2
        else:
            return -0.3

    density_str = str(density).lower()
    adjustments = {"low": 0.3, "medium": 0.0, "high": -0.2, "extreme": -0.3}
    return adjustments.get(density_str, 0.0)


def compute_composite(dimensions: dict[str, int], track: str = "", entry: dict | None = None) -> float:
    """Compute weighted composite score from dimensions.

    Uses job-specific weights when track is "job", creative weights otherwise.
    When entry is provided, applies applicant density adjustment.
    """
    weights = get_weights(track)
    total = 0.0
    for dim, weight in weights.items():
        val = dimensions.get(dim, 5)
        total += val * weight
    if entry is not None:
        total += applicant_density_adjustment(entry)
    return round(max(0, min(total, 10)), 1)


def scoring_confidence_band(n_outcomes: int, calibration_target: int = 50) -> float:
    """Compute a confidence band (±X) on composite scores.

    The band narrows as outcome data accumulates. With 0 outcomes, the band is
    ±1.5 (weights are purely theoretical). At calibration_target outcomes, the
    band shrinks to ±0.3 (weights are empirically validated).

    Uses a simple inverse-sqrt decay: band = max_band / sqrt(1 + n_outcomes).
    """
    import math
    max_band = 1.5
    min_band = 0.3
    if n_outcomes >= calibration_target:
        return min_band
    band = max_band / math.sqrt(1 + n_outcomes)
    return round(max(band, min_band), 1)


# Below this composite score, recommend skipping the application
QUALIFICATION_THRESHOLD = 5.0
JOB_QUALIFICATION_THRESHOLD = 5.5


def get_weights(track: str) -> dict:
    """Return the weight config appropriate for the entry's track.

    If a calibration file exists with sufficient outcome data (n>=10),
    blends calibrated weights at 30% with base weights at 70%.
    """
    if track == "job":
        base = WEIGHTS_JOB
    elif track in _CONSULTING_TRACKS:
        base = WEIGHTS_CONSULTING
    elif track in _GRANT_TRACKS:
        base = WEIGHTS_GRANT
    else:
        base = WEIGHTS  # fallback to grant weights (legacy default)

    try:
        from outcome_learner import load_calibration
        cal = load_calibration()
        if cal and cal.get("sufficient_data"):
            cal_weights = cal["weights"]
            # Blend: 70% base + 30% calibrated
            blended = {}
            for dim in base:
                base_val = base[dim]
                cal_val = cal_weights.get(dim, base_val)
                blended[dim] = round(base_val * 0.70 + cal_val * 0.30, 4)
            # Normalize to sum to 1.0
            total = sum(blended.values())
            if total > 0:
                blended = {k: round(v / total, 4) for k, v in blended.items()}
            return blended
    except ImportError:
        pass

    return base


def get_qualification_threshold(track: str) -> float:
    """Return the qualification threshold appropriate for the entry's track."""
    return JOB_QUALIFICATION_THRESHOLD if track == "job" else QUALIFICATION_THRESHOLD


def qualify(entry: dict, all_entries: list[dict] | None = None) -> tuple[bool, str]:
    """Return (should_apply, reason) based on composite score.

    Uses track-appropriate weights and threshold: job entries use
    JOB_QUALIFICATION_THRESHOLD (5.5) with job weights, creative entries
    use QUALIFICATION_THRESHOLD (5.0) with creative weights.
    """
    track = entry.get("track", "")
    threshold = get_qualification_threshold(track)
    dimensions = compute_dimensions(entry, all_entries)
    composite = compute_composite(dimensions, track, entry=entry)

    if composite >= threshold:
        return True, f"composite {composite:.1f} >= {threshold}"

    # Find the weakest dimensions to explain why
    weak = sorted(
        ((dim, dimensions[dim]) for dim in DIMENSION_ORDER),
        key=lambda x: x[1],
    )
    weak_names = [f"{dim}={val}" for dim, val in weak[:3]]
    return False, f"composite {composite:.1f} < {threshold} (weak: {', '.join(weak_names)})"


def update_entry_file(filepath: Path, dimensions: dict[str, int], composite: float, dry_run: bool = False):
    """Update a pipeline YAML file with new dimensions and composite score.

    Preserves original_score for manual entries (non-auto-sourced) to break
    the circular dependency between fit.score and dimension estimation.
    Uses targeted regex to preserve file formatting while verifying
    the result is still valid YAML after each modification.
    """
    import re

    from pipeline_lib import update_yaml_field

    with open(filepath) as f:
        content = f.read()

    data = yaml.safe_load(content)
    fit = data.get("fit", {}) if isinstance(data.get("fit"), dict) else {}
    raw_score = fit.get("score")
    old_score = float(raw_score) if raw_score is not None else None
    tags = data.get("tags") or []

    if dry_run:
        return old_score, composite

    # Backfill original_score for manual entries that don't have it yet.
    # Only for non-auto-sourced entries with existing dimensions (already scored once).
    has_original = fit.get("original_score") is not None
    has_dimensions = isinstance(fit.get("dimensions"), dict)
    is_auto = "auto-sourced" in tags

    if not has_original and not is_auto and has_dimensions and old_score is not None:
        # Insert original_score line right after the score line (anchored to fit: section)
        fit_pos = content.find("\nfit:")
        search_start = fit_pos + 1 if fit_pos >= 0 else 0
        score_pattern = re.compile(r"^(\s+)(score:\s+\S+)\s*$", re.MULTILINE)
        match = score_pattern.search(content, search_start)
        if match:
            indent = match.group(1)
            insert_after = match.end()
            original_line = f"\n{indent}original_score: {old_score}"
            content = content[:insert_after] + original_line + content[insert_after:]

    # Update score via safe helper
    content = update_yaml_field(content, "score", str(composite), nested=True)

    # Build new dimensions block
    # Detect the indentation used in the file for fit sub-keys
    fit_indent_match = re.search(r"^(\s+)score:", content, re.MULTILINE)
    indent = fit_indent_match.group(1) if fit_indent_match else "  "
    dim_indent = indent + "  "

    new_dims_lines = [f"{indent}dimensions:"]
    for key in DIMENSION_ORDER:
        new_dims_lines.append(f"{dim_indent}{key}: {dimensions[key]}")
    new_dims_block = "\n".join(new_dims_lines)

    # Replace existing dimensions block or insert before next top-level key after fit
    dims_pattern = re.compile(
        r"^(\s+dimensions:\s*\n)"  # dimensions: header
        r"(?:\s+\w+:\s*\d+\s*\n)*",  # dimension key-value lines
        re.MULTILINE,
    )

    if dims_pattern.search(content):
        content = dims_pattern.sub(new_dims_block + "\n", content, count=1)
    else:
        # No dimensions block exists — insert after the last fit sub-key
        # Find the fit section and its last indented line
        fit_section = re.search(
            r"^fit:\s*\n((?:\s+\S.*\n)*)",
            content,
            re.MULTILINE,
        )
        if fit_section:
            insert_pos = fit_section.end()
            content = content[:insert_pos] + new_dims_block + "\n" + content[insert_pos:]

    # Verify the final content is still valid YAML
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML became invalid after scoring update: {e}")

    atomic_write(filepath, content)

    return old_score, composite


def _print_qualify_group(label: str, threshold: float,
                         apply_list: list, skip_list: list):
    """Print a single qualification group (job or creative)."""
    print(f"{label} (threshold: {threshold})")
    print(f"{'-' * 50}")

    if apply_list:
        print("APPLY:")
        for eid, reason in sorted(apply_list, key=lambda x: x[1], reverse=True):
            print(f"  {eid:<40s} {reason}")

    if skip_list:
        print("SKIP:")
        for eid, reason in sorted(skip_list, key=lambda x: x[1]):
            print(f"  {eid:<40s} {reason}")

    print(f"  {len(apply_list)} APPLY | {len(skip_list)} SKIP")
    print()


def run_qualify(entries: list[tuple[Path, dict]]):
    """Print APPLY/SKIP recommendations grouped by track type."""
    job_apply = []
    job_skip = []
    creative_apply = []
    creative_skip = []

    all_raw = [d for _, d in entries]
    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        should_apply, reason = qualify(data, all_entries=all_raw)

        if track == "job":
            (job_apply if should_apply else job_skip).append((entry_id, reason))
        else:
            (creative_apply if should_apply else creative_skip).append((entry_id, reason))

    if job_apply or job_skip:
        _print_qualify_group(
            "JOB ENTRIES", JOB_QUALIFICATION_THRESHOLD,
            job_apply, job_skip,
        )

    if creative_apply or creative_skip:
        _print_qualify_group(
            "CREATIVE ENTRIES", QUALIFICATION_THRESHOLD,
            creative_apply, creative_skip,
        )

    print(f"{'=' * 50}")
    total_apply = len(job_apply) + len(creative_apply)
    total_skip = len(job_skip) + len(creative_skip)
    print(f"Total: {total_apply} APPLY | {total_skip} SKIP")


def get_auto_qualify_min() -> float:
    """Return the auto-qualify minimum score, mode-aware.

    Checks mode_thresholds from market intelligence first, then falls back
    to the rubric-defined AUTO_QUALIFY_MIN.
    """
    try:
        from pipeline_lib import get_mode_thresholds
        t = get_mode_thresholds()
        return float(t.get("auto_qualify_min", AUTO_QUALIFY_MIN))
    except ImportError:
        return AUTO_QUALIFY_MIN


# NYC-metro keywords for location matching
_NYC_METRO_KEYWORDS = frozenset({
    "new york", "nyc", "manhattan", "brooklyn", "staten island", "queens",
    "bronx", "jersey city", "newark", "hoboken", "weehawken",
    "long island city", "astoria", "williamsburg",
})


def _is_acceptable_location(entry: dict) -> bool:
    """Check if a job entry's location is remote or NYC-metro.

    Returns True for: remote, us-remote, hybrid-remote, or any location
    containing NYC-metro keywords. Returns True for non-job tracks (grants etc).
    """
    if entry.get("track") != "job":
        return True

    loc = (entry.get("target", {}).get("location", "") or "").lower()
    loc_class = (entry.get("target", {}).get("location_class", "") or "").lower()

    # Remote is acceptable only if it includes US/USA/United States
    if "remote" in loc or "remote" in loc_class:
        # "Remote" alone is ambiguous — need US qualifier
        us_markers = {"usa", "us", "united states", "u.s", "america", "new york", "nyc"}
        loc_words = loc.lower()
        if any(m in loc_words for m in us_markers):
            return True
        # "Remote" with no country qualifier — check location_class
        if "us" in loc_class or "usa" in loc_class:
            return True
        # Bare "Remote" with no US signal — reject
        if loc.strip().lower() in {"remote", "remote "}:
            return False
        # Has other text besides remote — let it through (benefit of doubt)
        return True

    # NYC-metro is acceptable
    for kw in _NYC_METRO_KEYWORDS:
        if kw in loc:
            return True

    # No location data — let it through (benefit of the doubt for new entries)
    if not loc and not loc_class:
        return True

    return False


def run_auto_qualify(dry_run: bool = False, yes: bool = False,
                     min_score: float | None = None, limit: int = 0):
    """Batch-advance qualifying research_pool entries to qualified in active/.

    Loads entries from research_pool/, runs qualify() on each, filters by
    min_score, and moves qualifying entries back to active/ with status=qualified.

    Defaults to dry-run unless --yes is explicitly passed to prevent accidental
    mass-promotion of entries into active/.

    Args:
        dry_run: If True, show preview without moving files.
        yes: If True, execute the moves. Without --yes or --dry-run, defaults to dry-run.
        min_score: Minimum composite score for auto-qualify (default from mode thresholds).
        limit: Maximum entries to promote (0 = unlimited). Highest scores first.
    """
    if min_score is None:
        min_score = get_auto_qualify_min()
    import shutil

    # Default to dry-run unless --yes is explicitly passed
    if not dry_run and not yes:
        dry_run = True
        print("(Defaulting to dry-run. Use --yes to execute.)\n")

    pool_entries = _load_entries_raw(
        dirs=[PIPELINE_DIR_RESEARCH_POOL], include_filepath=True,
    )
    if not pool_entries:
        print("No entries in research_pool/.")
        summary = {
            "dry_run": dry_run,
            "executed": not dry_run,
            "pool_entries": 0,
            "qualified_candidates": 0,
            "below_min_score": 0,
            "skipped": 0,
            "moved": 0,
            "min_score": min_score,
            "limit": limit,
        }
        _score_telemetry.log_score_run("auto_qualify", summary)
        return summary

    # Pre-load all raw entries for cross-pipeline scoring signals
    all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)

    qualified_list = []
    skipped = 0
    below_min_score = 0

    for entry in pool_entries:
        filepath = entry.get("_filepath")
        if not filepath:
            continue
        entry_id = entry.get("id", filepath.stem)
        should_apply, reason = qualify(entry, all_raw)

        if not should_apply:
            skipped += 1
            continue

        # Skip stale job entries — they'd be immediately flushed by the freshness gate
        track = entry.get("track", "")
        if track == "job":
            from pipeline_freshness import _load_freshness_thresholds, get_posting_age_hours
            _, _, stale_hours = _load_freshness_thresholds()
            age = get_posting_age_hours(entry)
            if age is not None and age > stale_hours:
                skipped += 1
                continue

            # Skip job entries outside acceptable locations (remote or NYC-metro)
            if not _is_acceptable_location(entry):
                skipped += 1
                continue

        # Fresh-compute score instead of reading stale YAML value
        dims = compute_dimensions(entry, all_raw)
        score = compute_composite(dims, track, entry=entry)
        if score < min_score:
            below_min_score += 1
            continue

        qualified_list.append((filepath, entry_id, entry, reason, score))

    # Sort by score descending so highest-scoring entries are promoted first
    qualified_list.sort(key=lambda x: x[4], reverse=True)

    # Apply limit
    if limit > 0 and len(qualified_list) > limit:
        qualified_list = qualified_list[:limit]

    print(f"Research pool: {len(pool_entries)} entries")
    print(f"Qualify (score >= {min_score}): {len(qualified_list)} | Below min-score: {below_min_score} | Skip: {skipped}")
    if limit > 0:
        print(f"Limit: {limit}")
    print()

    if not qualified_list:
        print("No entries meet the qualification threshold.")
        summary = {
            "dry_run": dry_run,
            "executed": not dry_run,
            "pool_entries": len(pool_entries),
            "qualified_candidates": 0,
            "below_min_score": below_min_score,
            "skipped": skipped,
            "moved": 0,
            "min_score": min_score,
            "limit": limit,
        }
        _score_telemetry.log_score_run("auto_qualify", summary)
        return summary

    PIPELINE_DIR_ACTIVE.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    moved = 0
    for filepath, entry_id, entry, reason, score in qualified_list:
        dest = PIPELINE_DIR_ACTIVE / filepath.name

        if dry_run:
            print(f"  [dry-run] {entry_id} (score={score}, {reason}) -> active/ as qualified")
        else:
            # Update status, score, dimensions, and timestamps
            content = filepath.read_text()
            content = update_yaml_field(content, "status", "qualified")
            try:
                content = update_yaml_field(content, "score", str(score), nested=True, parent_key="fit")
            except ValueError:
                pass  # fit.score field may not exist in template
            content = update_last_touched(content)
            try:
                content = update_yaml_field(content, "qualified", f'"{today_str}"', nested=True)
            except ValueError:
                pass  # timeline section may not have a qualified field — that's OK
            atomic_write(filepath, content)
            # Move to active/
            shutil.move(str(filepath), str(dest))
            print(f"  {entry_id} -> active/ (score={score}, qualified, {reason})")
        moved += 1

    print(f"\n{'=' * 50}")
    if dry_run:
        print(f"Would auto-qualify {moved} entries (dry run)")
        print("Run with --yes to execute")
    else:
        print(f"Auto-qualified {moved} entries to active/")
    summary = {
        "dry_run": dry_run,
        "executed": not dry_run,
        "pool_entries": len(pool_entries),
        "qualified_candidates": len(qualified_list),
        "below_min_score": below_min_score,
        "skipped": skipped,
        "moved": moved,
        "min_score": min_score,
        "limit": limit,
    }
    _score_telemetry.log_score_run("auto_qualify", summary)
    return summary


RUBRIC_DESCRIPTIONS = _score_explain.RUBRIC_DESCRIPTIONS


def _rubric_desc(dim: str, score: int) -> str:
    return _score_explain._rubric_desc(dim, score)


def explain_entry(entry: dict, all_entries: list[dict] | None = None) -> str:
    return _score_explain.explain_entry(
        entry,
        all_entries,
        get_weights=get_weights,
        compute_dimensions=compute_dimensions,
        compute_composite=compute_composite,
        compute_human_dimensions=compute_human_dimensions,
        score_network_proximity=score_network_proximity,
        score_financial_alignment=score_financial_alignment,
        score_effort_to_value=score_effort_to_value,
        score_strategic_value=score_strategic_value,
        score_deadline_feasibility=score_deadline_feasibility,
        score_portal_friction=score_portal_friction,
        dimension_order=DIMENSION_ORDER,
        pillar_scorers=_PILLAR_SCORERS,
    )


def review_compressed(entries: list[tuple[Path, dict]], lo: float = 6.5, hi: float = 7.5):
    return _score_explain.review_compressed(entries, lo=lo, hi=hi)


_NETWORK_LEVELS = [
    *(_score_reachability._NETWORK_LEVELS),
]


def analyze_reachability(
    entry: dict,
    all_entries: list[dict] | None = None,
    threshold: float = 9.0,
) -> dict:
    return _score_reachability.analyze_reachability(
        entry,
        all_entries,
        threshold=threshold,
        compute_dimensions=compute_dimensions,
        compute_composite=compute_composite,
    )


def run_reachable(threshold: float = 9.0):
    summary = _score_reachability.run_reachable(
        threshold=threshold,
        load_entries_raw=_load_entries_raw,
        all_pipeline_dirs_with_pool=ALL_PIPELINE_DIRS_WITH_POOL,
        analyze_reachability_fn=analyze_reachability,
    )
    _score_telemetry.log_score_run("reachable", summary)
    return summary


def run_triage_staged(
    dry_run: bool = True,
    yes: bool = False,
    submit_threshold: float = 8.5,
    demote_threshold: float = 7.0,
):
    summary = _score_reachability.run_triage_staged(
        dry_run=dry_run,
        yes=yes,
        submit_threshold=submit_threshold,
        demote_threshold=demote_threshold,
        load_entries_raw=_load_entries_raw,
        all_pipeline_dirs_with_pool=ALL_PIPELINE_DIRS_WITH_POOL,
        compute_dimensions=compute_dimensions,
        compute_composite=compute_composite,
        analyze_reachability_fn=analyze_reachability,
        update_yaml_field=update_yaml_field,
        update_last_touched=update_last_touched,
        atomic_write=atomic_write,
    )
    _score_telemetry.log_score_run("triage_staged", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Score pipeline entries against rubric")
    parser.add_argument("--target", help="Score a single entry by ID")
    parser.add_argument("--all", action="store_true",
                        help="Score all entries in active/submitted/closed (NOT research_pool)")
    parser.add_argument("--include-pool", action="store_true",
                        help="Include research_pool in --all scoring (usually not needed)")
    parser.add_argument("--qualify", action="store_true",
                        help="Show APPLY/SKIP recommendations based on score threshold")
    parser.add_argument("--explain", action="store_true",
                        help="Show detailed score derivation for a single entry (requires --target)")
    parser.add_argument("--review-compressed", action="store_true",
                        help="List entries in compressed score band for manual dimension review")
    parser.add_argument("--auto-qualify", action="store_true",
                        help="Batch-advance qualifying research_pool entries to active/qualified")
    parser.add_argument("--reachable", action="store_true",
                        help="Show reachability analysis for all actionable entries")
    parser.add_argument("--threshold", type=float, default=9.0,
                        help="Score threshold for reachability analysis (default: 9.0)")
    parser.add_argument("--triage-staged", action="store_true",
                        help="Triage staged entries into submit-ready / hold / demote")
    parser.add_argument("--demote", action="store_true",
                        help="Execute demotions (with --triage-staged --yes)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show scores without writing changes")
    parser.add_argument("--yes", action="store_true",
                        help="Execute changes (used with --auto-qualify, --triage-staged)")
    parser.add_argument("--min-score", type=float, default=AUTO_QUALIFY_MIN,
                        help=f"Minimum score for auto-qualify (default: {AUTO_QUALIFY_MIN})")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max entries to auto-qualify (0 = unlimited)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-dimension breakdowns")
    args = parser.parse_args()

    if not (args.target or args.all or args.qualify or args.explain
            or args.review_compressed or args.auto_qualify
            or args.reachable or args.triage_staged):
        parser.error("Specify --target, --all, --qualify, --explain, --review-compressed, "
                     "--auto-qualify, --reachable, or --triage-staged")

    if args.explain and not args.target:
        parser.error("--explain requires --target <id>")

    # --qualify implies --all unless --target is given
    if args.qualify and not args.target:
        args.all = True

    # --auto-qualify is a standalone command
    if args.auto_qualify:
        run_auto_qualify(
            dry_run=args.dry_run,
            yes=args.yes,
            min_score=args.min_score,
            limit=args.limit,
        )
        return

    # --reachable is a standalone command
    if args.reachable:
        run_reachable(threshold=args.threshold)
        return

    # --triage-staged is a standalone command
    if args.triage_staged:
        run_triage_staged(dry_run=args.dry_run, yes=args.yes)
        return

    # --review-compressed implies --all
    if args.review_compressed:
        args.all = True

    # --all scores active/submitted/closed only. Research pool entries are
    # scored exclusively via --auto-qualify (which has its own loading logic).
    # Use --include-pool to explicitly rescore research_pool entries in-place.
    include_pool = getattr(args, "include_pool", False) and not args.target
    entries = load_entries(args.target if args.target else None, include_pool=include_pool)
    if not entries:
        print("No entries found.", file=sys.stderr)
        sys.exit(1)

    # Pre-load all raw entries for cross-pipeline signals (track experience)
    all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)

    if args.explain:
        _, data = entries[0]
        print(explain_entry(data, all_raw))
        return

    if args.review_compressed:
        review_compressed(entries)
        return

    if args.qualify:
        run_qualify(entries)
        return

    changes = []
    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        dimensions = compute_dimensions(data, all_raw)
        composite = compute_composite(dimensions, track, entry=data)

        # Track network_proximity changes for ROI logging
        old_dims = data.get("fit", {}).get("dimensions", {}) if isinstance(data.get("fit"), dict) else {}
        old_network = old_dims.get("network_proximity", 1) if isinstance(old_dims, dict) else 1

        old_score, new_score = update_entry_file(filepath, dimensions, composite, dry_run=args.dry_run)

        if not args.dry_run:
            _log_network_change(entry_id, old_network, dimensions.get("network_proximity", 1), filepath)

        delta = ""
        if old_score is not None:
            diff = new_score - old_score
            if abs(diff) >= 0.5:
                delta = f" (was {old_score}, delta {diff:+.1f})"
            else:
                delta = f" (was {old_score}, ~same)"

        changes.append((entry_id, old_score, new_score, dimensions))

        rubric = "JOB" if track == "job" else "CREATIVE"
        weights = get_weights(track)

        if args.verbose:
            print(f"\n{'=' * 50}")
            print(f"{entry_id}: {new_score}{delta}  [{rubric} rubric]")
            print(f"  {'Dimension':<25s} {'Score':>5s}  {'Weight':>6s}  {'Contrib':>7s}")
            print(f"  {'-' * 25} {'-' * 5}  {'-' * 6}  {'-' * 7}")
            for dim in DIMENSION_ORDER:
                val = dimensions[dim]
                weight = weights.get(dim)
                if weight is None:
                    continue  # dimension not weighted for this track (e.g. consulting omits portal_friction)
                contrib = val * weight
                print(f"  {dim:<25s} {int(val):>5d}  {weight:>5.0%}  {contrib:>7.2f}")
            print(f"  {'COMPOSITE':<25s}        {'':>6s}  {new_score:>7.1f}")
        else:
            print(f"  {entry_id:<40s} {new_score:>5.1f}{delta}  [{rubric}]")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Scored {len(changes)} entries" + (" (dry run)" if args.dry_run else ""))

    # Model maturity indicator — count terminal outcomes for calibration status
    all_entries = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    terminal_outcomes = {"accepted", "rejected", "withdrawn", "expired"}
    n_outcomes = sum(1 for e in all_entries if e.get("outcome") in terminal_outcomes)
    calibration_target = 50
    if n_outcomes >= calibration_target:
        maturity = "CALIBRATED"
    else:
        maturity = "PENDING"
    band = scoring_confidence_band(n_outcomes, calibration_target)
    print(f"Model maturity: {maturity} (N={n_outcomes} outcomes; target N={calibration_target})")
    print(f"Score confidence: ±{band} (scores are composite ± this band until calibrated)")

    if not args.dry_run:
        significant = [(eid, old, new, d) for eid, old, new, d in changes
                        if old is not None and abs(new - old) >= 1.0]
        if significant:
            print("\nSignificant changes (>= 1.0 delta):")
            for eid, old, new, _ in sorted(significant, key=lambda x: abs(x[2] - x[1]), reverse=True):
                print(f"  {eid:<40s} {old} -> {new} ({new - old:+.1f})")


def recalibrate_weights(entries: list[dict] | None = None) -> dict[str, float] | None:
    """Analyze actual outcomes to suggest weight recalibration.

    Compares dimension scores of accepted vs rejected entries to identify
    which dimensions best predict positive outcomes.

    Returns a suggested weight dict, or None if insufficient data.
    """
    if entries is None:
        entries = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)

    # Split by outcome
    accepted = []
    rejected = []
    for e in entries:
        outcome = e.get("outcome")
        dims = e.get("fit", {}).get("dimensions") if isinstance(e.get("fit"), dict) else None
        if not isinstance(dims, dict) or not dims:
            continue
        if outcome == "accepted":
            accepted.append(dims)
        elif outcome == "rejected":
            rejected.append(dims)

    if len(accepted) < 2 or len(rejected) < 2:
        return None  # insufficient data

    # Compute mean dimension score for each outcome group
    dim_names = list(DIMENSION_ORDER)
    accepted_means: dict[str, float] = {}
    rejected_means: dict[str, float] = {}

    for dim in dim_names:
        a_vals = [d.get(dim, 5) for d in accepted if isinstance(d.get(dim), (int, float))]
        r_vals = [d.get(dim, 5) for d in rejected if isinstance(d.get(dim), (int, float))]
        accepted_means[dim] = sum(a_vals) / len(a_vals) if a_vals else 5.0
        rejected_means[dim] = sum(r_vals) / len(r_vals) if r_vals else 5.0

    # Compute discriminative power: how much each dimension separates outcomes
    deltas = {}
    for dim in dim_names:
        deltas[dim] = max(0.01, accepted_means[dim] - rejected_means[dim])

    # Normalize deltas to suggested weights
    total_delta = sum(deltas.values())
    suggested = {dim: round(deltas[dim] / total_delta, 3) for dim in dim_names}

    return suggested


if __name__ == "__main__":
    main()
