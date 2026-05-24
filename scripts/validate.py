#!/usr/bin/env python3
"""Validate pipeline YAML entries against the schema."""

import sys
from pathlib import Path

import yaml
from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL as PIPELINE_DIRS,
)
from pipeline_lib import (
    REPO_ROOT,
    VALID_DIMENSIONS,
    VALID_STATUSES,
    VALID_TRACKS,
    VALID_TRANSITIONS,
    detect_portal,
)

REQUIRED_FIELDS = {"id", "name", "track", "status"}
VALID_OUTCOMES = {"accepted", "rejected", "withdrawn", "expired", None}
VALID_DEADLINE_TYPES = {"hard", "rolling", "window", "tba", "fixed"}
VALID_TIMEZONES = {"ET", "CT", "MT", "PT", "EST", "CST", "MST", "PST", "EDT", "CDT", "MDT", "PDT", "UTC", "GMT"}
VALID_PORTALS = {
    "submittable", "slideroom", "email", "custom", "web", "greenhouse",
    "workable", "lever", "ashby", "smartrecruiters",
    # Native ATS portals (2026-03-25)
    "cursor-native", "notion-native",
}
VALID_AMOUNT_TYPES = {"lump_sum", "stipend", "salary", "fee", "in_kind", "variable"}
VALID_POSITIONS = {
    "systems-artist", "creative-technologist", "educator",
    "community-practitioner", "independent-engineer",
    # Added 2026-03-25: full 9-position canonical set from strategy/identity-positions.md
    "documentation-engineer", "governance-architect",
    "platform-orchestrator", "founder-operator",
}
VALID_EFFORT_LEVELS = {"quick", "standard", "deep", "complex"}
VALID_OUTREACH_TYPES = {
    "pre_submission", "warm_contact", "info_session",
    "post_submission", "follow_up", "reference_request",
}
VALID_OUTREACH_CHANNELS = {"email", "linkedin", "phone", "in_person", "webinar", "other"}
VALID_OUTREACH_STATUSES = {"planned", "done", "waiting"}
VALID_RECOMMENDATION_STATUSES = {"not_asked", "asked", "confirmed", "submitted", "declined"}
VALID_PORTAL_FIELD_FORMATS = {"text", "textarea", "file_upload", "url", "dropdown", "checkbox"}
VALID_WITHDRAWAL_REASONS = {
    "missed_deadline", "low_fit", "effort_too_high", "duplicate",
    "ineligible", "strategic_shift", "personal", "other",
}
VALID_DEFERRAL_REASONS = {
    "portal_paused", "cycle_not_open", "pending_materials",
    "external_dependency", "strategic_hold",
    "below_actionable_threshold", "below_threshold",
}
VALID_LOCATION_CLASSES = {"us-onsite", "us-remote", "remote-global", "international", "unknown"}
SCORING_RUBRIC_PATH = REPO_ROOT / "strategy" / "scoring-rubric.yaml"


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping_no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key ({key!r})",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def load_yaml_strict(text: str):
    """Parse YAML and fail on duplicate keys."""
    return yaml.load(text, Loader=_UniqueKeyLoader)

def _reachable_statuses(from_status: str) -> set[str]:
    """Return all statuses reachable from a given status via valid transitions."""
    reachable = set()
    frontier = [from_status]
    while frontier:
        current = frontier.pop()
        for next_status in VALID_TRANSITIONS.get(current, set()):
            if next_status not in reachable:
                reachable.add(next_status)
                frontier.append(next_status)
    return reachable


def validate_entry(filepath: Path, warnings: list[str] | None = None) -> list[str]:
    """Validate a single pipeline YAML file. Returns list of errors.

    Optionally collects non-fatal warnings into the provided list.
    """
    errors = []

    try:
        with open(filepath) as f:
            data = load_yaml_strict(f.read())
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["File does not contain a YAML mapping"]

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # ID matches filename
    expected_id = filepath.stem
    if data.get("id") and data["id"] != expected_id:
        errors.append(f"id '{data['id']}' does not match filename '{expected_id}'")

    # Track validation
    track = data.get("track")
    if track and track not in VALID_TRACKS:
        errors.append(f"Invalid track: '{track}' (valid: {VALID_TRACKS})")

    # Status validation
    status = data.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status: '{status}' (valid: {VALID_STATUSES})")

    # Outcome validation
    outcome = data.get("outcome")
    if outcome not in VALID_OUTCOMES:
        errors.append(f"Invalid outcome: '{outcome}' (valid: {VALID_OUTCOMES})")

    # Deadline type and timezone
    deadline = data.get("deadline", {})
    if isinstance(deadline, dict):
        dtype = deadline.get("type")
        if dtype and dtype not in VALID_DEADLINE_TYPES:
            errors.append(f"Invalid deadline.type: '{dtype}'")
        dtime = deadline.get("time")
        ddate = deadline.get("date")
        if isinstance(dtime, str) and dtime.strip():
            # Extract timezone abbreviation from time string (e.g. "15:00 ET" → "ET")
            parts = dtime.strip().split()
            if len(parts) >= 2:
                tz = parts[-1]
                if tz not in VALID_TIMEZONES and warnings is not None:
                    warnings.append(f"Unrecognized deadline timezone: '{tz}' (expected one of {sorted(VALID_TIMEZONES)})")
            elif len(parts) == 1 and warnings is not None:
                # Time present but no timezone (e.g., "15:00" without "ET")
                warnings.append(f"Deadline time '{dtime}' has no timezone — add one (e.g., ET, PT, UTC)")
        elif ddate and dtype == "hard" and not dtime and warnings is not None:
            # Hard deadline with a date but no time at all
            warnings.append("Hard deadline has no time/timezone — risk of missing cutoff")

    # Amount type
    amount = data.get("amount", {})
    if isinstance(amount, dict):
        atype = amount.get("type")
        if atype and atype not in VALID_AMOUNT_TYPES:
            errors.append(f"Invalid amount.type: '{atype}'")

    # Fit validation
    fit = data.get("fit", {})
    if isinstance(fit, dict):
        score = fit.get("score")
        # 0 is a valid sentinel meaning "not yet scored" (auto-sourced entries)
        if score is not None and isinstance(score, (int, float)) and score != 0 and not (1 <= score <= 10):
            errors.append(f"Fit score out of range: {score} (must be 0 or 1-10)")
        original_score = fit.get("original_score")
        if original_score is not None and isinstance(original_score, (int, float)) and original_score != 0 and not (1 <= original_score <= 10):
            errors.append(f"Fit original_score out of range: {original_score} (must be 0 or 1-10)")
        position = fit.get("identity_position")
        if position and position not in VALID_POSITIONS:
            errors.append(f"Invalid identity_position: '{position}'")
        # Validate dimensions if present
        dimensions = fit.get("dimensions")
        if dimensions is not None:
            if not isinstance(dimensions, dict):
                errors.append("fit.dimensions must be a mapping")
            else:
                for key, val in dimensions.items():
                    if key not in VALID_DIMENSIONS:
                        errors.append(f"Unknown dimension: '{key}' (valid: {VALID_DIMENSIONS})")
                    if val is not None and isinstance(val, (int, float)) and not (1 <= val <= 10):
                        errors.append(f"Dimension '{key}' out of range: {val} (must be 1-10)")

    # Effort level validation
    submission = data.get("submission", {})
    if isinstance(submission, dict):
        effort = submission.get("effort_level")
        if effort is not None and effort not in VALID_EFFORT_LEVELS:
            errors.append(f"Invalid effort_level: '{effort}' (valid: {VALID_EFFORT_LEVELS})")

    # Status transition validation
    status = data.get("status")
    if status and status in VALID_TRANSITIONS:
        timeline = data.get("timeline", {})
        if isinstance(timeline, dict):
            # Check that the current status is reachable from the timeline evidence
            # The timeline records when each stage was reached; if a later stage
            # has a date but an earlier required stage doesn't, that's suspicious
            stage_order = ["researched", "qualified", "materials_ready", "submitted",
                           "acknowledged", "interview", "outcome_date"]
            stage_to_status = {
                "researched": "research",
                "qualified": "qualified",
                "materials_ready": "staged",
                "submitted": "submitted",
                "acknowledged": "acknowledged",
                "interview": "interview",
                "outcome_date": "outcome",
            }
            # Find the highest stage with a date set
            highest_dated = None
            for stage_key in stage_order:
                if timeline.get(stage_key):
                    highest_dated = stage_to_status.get(stage_key)
            # If timeline shows a stage that can't reach current status, flag it.
            # However, entries can be demoted by triage (staged→qualified→research)
            # or deferred, retaining timeline history. Only flag when the current
            # status is genuinely unreachable AND not a backward demotion.
            status_rank = {
                "research": 0, "qualified": 1, "drafting": 2, "staged": 3,
                "deferred": -1,  # side state, always valid
                "submitted": 4, "acknowledged": 5, "interview": 6, "outcome": 7,
                "withdrawn": -1,  # terminal side state
            }
            if highest_dated and status in VALID_TRANSITIONS:
                reachable = _reachable_statuses(highest_dated)
                cur_rank = status_rank.get(status, -1)
                high_rank = status_rank.get(highest_dated, -1)
                # Only flag if status is forward of timeline evidence AND unreachable.
                # Backward movement (demotion) or side states are legitimate.
                if (status not in reachable and status != highest_dated
                        and cur_rank > high_rank and cur_rank >= 0):
                    errors.append(
                        f"Status '{status}' not reachable from timeline "
                        f"(highest dated stage: '{highest_dated}')"
                    )

            # Check chronological ordering of timeline dates
            from pipeline_lib import parse_date as _parse_date
            prev_key = None
            prev_dt = None
            for stage_key in stage_order:
                raw = timeline.get(stage_key)
                if not raw:
                    continue
                dt = _parse_date(raw)
                if dt is None:
                    continue
                if prev_dt is not None and dt < prev_dt:
                    errors.append(
                        f"Timeline out of order: '{stage_key}' ({dt}) "
                        f"before '{prev_key}' ({prev_dt})"
                    )
                prev_key = stage_key
                prev_dt = dt

    # Portal validation
    target = data.get("target", {})
    if isinstance(target, dict):
        portal = target.get("portal")
        if portal and portal not in VALID_PORTALS:
            errors.append(f"Invalid target.portal: '{portal}' (valid: {VALID_PORTALS})")
        # Location class validation (optional field)
        loc_class = target.get("location_class")
        if loc_class and loc_class not in VALID_LOCATION_CLASSES:
            errors.append(f"Invalid target.location_class: '{loc_class}' (valid: {VALID_LOCATION_CLASSES})")
        # Warn if portal doesn't match what URL detection finds
        app_url = target.get("application_url", "")
        if app_url and portal:
            detected = detect_portal(app_url)
            if detected and detected != portal:
                errors.append(
                    f"Portal mismatch: target.portal is '{portal}' but URL "
                    f"suggests '{detected}' ({app_url})"
                )

    # Block path validation
    submission = data.get("submission", {})
    if isinstance(submission, dict):
        blocks = submission.get("blocks_used", {})
        if isinstance(blocks, dict):
            from pipeline_lib import load_block_frontmatter
            REQUIRED_BLOCK_FRONTMATTER = {"title", "category", "tags", "identity_positions", "tracks", "tier"}
            for slot, block_path in blocks.items():
                full_path = REPO_ROOT / "blocks" / block_path
                # Check for .md extension
                if not full_path.suffix:
                    full_path = full_path.with_suffix(".md")
                if not full_path.exists():
                    errors.append(f"Block not found: blocks/{block_path} (slot: {slot})")
                else:
                    # Validate frontmatter completeness
                    fm = load_block_frontmatter(block_path)
                    if fm is None:
                        errors.append(f"Block missing frontmatter: blocks/{block_path} (slot: {slot})")
                    else:
                        missing_fm = REQUIRED_BLOCK_FRONTMATTER - set(fm.keys())
                        if missing_fm:
                            errors.append(
                                f"Block frontmatter missing fields {sorted(missing_fm)}: "
                                f"blocks/{block_path} (slot: {slot})"
                            )

    # last_touched validation
    last_touched = data.get("last_touched")
    if last_touched is not None:
        from datetime import datetime
        try:
            datetime.strptime(str(last_touched), "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid last_touched format: '{last_touched}' (expected YYYY-MM-DD)")

    # Outreach validation
    outreach = data.get("outreach")
    if outreach is not None:
        if not isinstance(outreach, list):
            errors.append("outreach must be a list")
        else:
            for i, item in enumerate(outreach):
                if not isinstance(item, dict):
                    errors.append(f"outreach[{i}] must be a mapping")
                    continue
                otype = item.get("type")
                if otype and otype not in VALID_OUTREACH_TYPES:
                    errors.append(f"outreach[{i}].type '{otype}' invalid (valid: {VALID_OUTREACH_TYPES})")
                ochannel = item.get("channel")
                if ochannel and ochannel not in VALID_OUTREACH_CHANNELS:
                    errors.append(f"outreach[{i}].channel '{ochannel}' invalid (valid: {VALID_OUTREACH_CHANNELS})")
                ostatus = item.get("status")
                if ostatus and ostatus not in VALID_OUTREACH_STATUSES:
                    errors.append(f"outreach[{i}].status '{ostatus}' invalid (valid: {VALID_OUTREACH_STATUSES})")

    # Recommendations validation
    recommendations = data.get("recommendations")
    if recommendations is not None:
        if not isinstance(recommendations, list):
            errors.append("recommendations must be a list")
        else:
            for i, rec in enumerate(recommendations):
                if not isinstance(rec, dict):
                    errors.append(f"recommendations[{i}] must be a mapping")
                    continue
                rstatus = rec.get("status")
                if rstatus and rstatus not in VALID_RECOMMENDATION_STATUSES:
                    errors.append(
                        f"recommendations[{i}].status '{rstatus}' invalid "
                        f"(valid: {VALID_RECOMMENDATION_STATUSES})"
                    )

    # Portal fields validation
    portal_fields = data.get("portal_fields")
    if portal_fields is not None:
        if not isinstance(portal_fields, dict):
            errors.append("portal_fields must be a mapping")
        else:
            fields = portal_fields.get("fields")
            if fields is not None:
                if not isinstance(fields, list):
                    errors.append("portal_fields.fields must be a list")
                else:
                    for i, field in enumerate(fields):
                        if not isinstance(field, dict):
                            errors.append(f"portal_fields.fields[{i}] must be a mapping")
                            continue
                        fmt = field.get("format")
                        if fmt and fmt not in VALID_PORTAL_FIELD_FORMATS:
                            errors.append(
                                f"portal_fields.fields[{i}].format '{fmt}' invalid "
                                f"(valid: {VALID_PORTAL_FIELD_FORMATS})"
                            )

    # Deferral field validation
    deferral = data.get("deferral")
    status = data.get("status")
    if status == "deferred" and deferral is None:
        if warnings is not None:
            warnings.append("Status is 'deferred' but no 'deferral' field present (recommended)")
    if deferral is not None:
        if not isinstance(deferral, dict):
            errors.append("deferral must be a mapping")
        else:
            reason = deferral.get("reason")
            if reason and reason not in VALID_DEFERRAL_REASONS:
                errors.append(
                    f"deferral.reason '{reason}' invalid "
                    f"(valid: {VALID_DEFERRAL_REASONS})"
                )
            resume_date = deferral.get("resume_date")
            if resume_date is not None:
                from datetime import datetime
                try:
                    datetime.strptime(str(resume_date), "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Invalid deferral.resume_date format: '{resume_date}' (expected YYYY-MM-DD)")

    # Governance status metadata validation
    status_meta = data.get("status_meta")
    reviewed_by = None
    approved_at = None
    submitted_by = None
    submitted_at = None
    if status_meta is not None:
        if not isinstance(status_meta, dict):
            errors.append("status_meta must be a mapping")
        else:
            reviewed_by = status_meta.get("reviewed_by")
            approved_by = status_meta.get("approved_by")
            submitted_by = status_meta.get("submitted_by")
            reviewed_at = status_meta.get("reviewed_at")
            approved_at = status_meta.get("approved_at")
            submitted_at = status_meta.get("submitted_at")

            if reviewed_by is not None and not isinstance(reviewed_by, str):
                errors.append("status_meta.reviewed_by must be a string")
            if approved_by is not None and not isinstance(approved_by, str):
                errors.append("status_meta.approved_by must be a string")
            if submitted_by is not None and not isinstance(submitted_by, str):
                errors.append("status_meta.submitted_by must be a string")

            from datetime import datetime
            if reviewed_at is not None:
                try:
                    datetime.strptime(str(reviewed_at), "%Y-%m-%d")
                except ValueError:
                    errors.append(
                        f"Invalid status_meta.reviewed_at format: '{reviewed_at}' "
                        "(expected YYYY-MM-DD)"
                    )
            if approved_at is not None:
                try:
                    datetime.strptime(str(approved_at), "%Y-%m-%d")
                except ValueError:
                    errors.append(
                        f"Invalid status_meta.approved_at format: '{approved_at}' "
                        "(expected YYYY-MM-DD)"
                    )
            if submitted_at is not None:
                try:
                    datetime.strptime(str(submitted_at), "%Y-%m-%d")
                except ValueError:
                    errors.append(
                        f"Invalid status_meta.submitted_at format: '{submitted_at}' "
                        "(expected YYYY-MM-DD)"
                    )

            if approved_at is not None and reviewed_by is None:
                errors.append("status_meta.approved_at requires status_meta.reviewed_by")
            if submitted_at is not None and submitted_by is None:
                errors.append("status_meta.submitted_at requires status_meta.submitted_by")

    if warnings is not None:
        if status == "staged":
            if not reviewed_by:
                warnings.append("status=staged missing status_meta.reviewed_by")
            if not approved_at:
                warnings.append("status=staged missing status_meta.approved_at")
        if status in {"submitted", "acknowledged", "interview", "outcome"}:
            if not submitted_by:
                warnings.append(f"status={status} missing status_meta.submitted_by")
            if not submitted_at:
                warnings.append(f"status={status} missing status_meta.submitted_at")

    # Withdrawal reason validation
    withdrawal = data.get("withdrawal_reason")
    if withdrawal is not None:
        if not isinstance(withdrawal, dict):
            errors.append("withdrawal_reason must be a mapping")
        else:
            reason = withdrawal.get("reason")
            if reason and reason not in VALID_WITHDRAWAL_REASONS:
                errors.append(
                    f"withdrawal_reason.reason '{reason}' invalid "
                    f"(valid: {VALID_WITHDRAWAL_REASONS})"
                )

    return errors


def check_profile_freshness() -> list[str]:
    """Compare profile JSON metric values against metrics-snapshot.md source of truth.

    Returns list of warning strings for stale profiles.
    """
    import re

    from pipeline_lib import BLOCKS_DIR, PROFILES_DIR

    warnings = []

    # Load source-of-truth metrics from metrics-snapshot.md
    snapshot_path = BLOCKS_DIR / "evidence" / "metrics-snapshot.md"
    if not snapshot_path.exists():
        warnings.append("Cannot check freshness: blocks/evidence/metrics-snapshot.md not found")
        return warnings

    snapshot = snapshot_path.read_text()

    # Extract canonical metrics from snapshot
    repo_match = re.search(r"Total repositories\s*\|\s*(\d+)", snapshot)
    canonical_repos = int(repo_match.group(1)) if repo_match else None

    test_match = re.search(r"Total test cases\s*\|\s*([\d,]+)", snapshot)
    canonical_tests = int(test_match.group(1).replace(",", "")) if test_match else None

    essay_match = re.search(r"Total essays\s*\|\s*(\d+)", snapshot)
    canonical_essays = int(essay_match.group(1)) if essay_match else None

    if not PROFILES_DIR.exists():
        warnings.append("Cannot check freshness: targets/profiles/ not found")
        return warnings

    stale_count = 0
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        if "index" in profile_path.name:
            continue
        text = profile_path.read_text()

        issues = []

        # Check for stale repo count
        if canonical_repos:
            stale_repos = re.findall(r"\b(\d+)(?:\s+|-)?repositor(?:ies|y)", text)
            for count_str in stale_repos:
                count = int(count_str)
                if count != canonical_repos:
                    issues.append(f"repo count {count} != {canonical_repos}")
                    break

        # Check for stale test count
        if canonical_tests:
            test_patterns = re.findall(r"\b([\d,]+)\s+(?:automated\s+)?test[s\s]", text)
            for t_str in test_patterns:
                t = int(t_str.replace(",", ""))
                if t != canonical_tests and t > 100:  # skip obvious subset refs
                    issues.append(f"test count {t:,} != {canonical_tests:,}")
                    break

        # Check for stale essay count
        if canonical_essays:
            essay_patterns = re.findall(r"\b(\d+)\s+essays?", text)
            for e_str in essay_patterns:
                e = int(e_str)
                if e != canonical_essays:
                    issues.append(f"essay count {e} != {canonical_essays}")
                    break

        if issues:
            stale_count += 1
            for issue in issues:
                warnings.append(f"  {profile_path.name}: {issue}")

    if stale_count:
        warnings.insert(0, f"STALE PROFILES — {stale_count} profile(s) with outdated metrics:")
    else:
        warnings.append("Profile freshness OK — all profiles match metrics-snapshot.md")

    return warnings


def validate_id_mappings() -> list[str]:
    """Validate PROFILE_ID_MAP and LEGACY_ID_MAP consistency.

    Checks:
    - Map values point to existing files
    - Map keys reference known entry IDs
    Returns list of error strings.
    """
    from pipeline_lib import (
        LEGACY_DIR,
        LEGACY_ID_MAP,
        PROFILE_ID_MAP,
        PROFILES_DIR,
    )

    errors = []

    # Check PROFILE_ID_MAP values exist
    if PROFILES_DIR.exists():
        profile_ids = {p.stem for p in PROFILES_DIR.glob("*.json") if "index" not in p.name}
        for entry_id, profile_id in PROFILE_ID_MAP.items():
            if profile_id not in profile_ids:
                errors.append(f"PROFILE_ID_MAP: '{entry_id}' -> '{profile_id}' but {profile_id}.json not found")

    # Check LEGACY_ID_MAP keys exist
    if LEGACY_DIR.exists():
        legacy_ids = {p.stem for p in LEGACY_DIR.glob("*.md")}
        for legacy_name in LEGACY_ID_MAP:
            if legacy_name not in legacy_ids:
                errors.append(f"LEGACY_ID_MAP: key '{legacy_name}' has no matching {legacy_name}.md")

    return errors


def validate_scoring_rubric(path: Path = SCORING_RUBRIC_PATH) -> list[str]:
    """Validate scoring-rubric.yaml structure and constraints."""
    errors: list[str] = []
    if not path.exists():
        return [f"Scoring rubric not found: {path}"]

    try:
        rubric = load_yaml_strict(path.read_text()) or {}
    except yaml.YAMLError as exc:
        return [f"Scoring rubric YAML parse error: {exc}"]

    if not isinstance(rubric, dict):
        return ["Scoring rubric must be a YAML mapping"]

    for section in ("weights", "weights_job"):
        weights = rubric.get(section)
        if not isinstance(weights, dict):
            errors.append(f"{section} must be a mapping")
            continue

        keys = set(weights.keys())
        # Three-pillar rubric: each weight set uses a pillar-specific SUBSET of
        # VALID_DIMENSIONS, so we only reject unknown dimensions (not absent ones).
        extra = sorted(keys - VALID_DIMENSIONS)
        if extra:
            errors.append(f"{section} has unknown dimensions: {extra}")

        total = 0.0
        for dim, value in weights.items():
            if not isinstance(value, (int, float)):
                errors.append(f"{section}.{dim} must be numeric, got {type(value).__name__}")
                continue
            if value < 0:
                errors.append(f"{section}.{dim} must be >= 0")
            total += float(value)

        if abs(total - 1.0) > 1e-6:
            errors.append(f"{section} must sum to 1.0 (got {total:.6f})")

    thresholds = rubric.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("thresholds must be a mapping")
    else:
        score_min = thresholds.get("score_range_min")
        score_max = thresholds.get("score_range_max")
        auto_q = thresholds.get("auto_qualify_min")
        tier1 = thresholds.get("tier1_cutoff")
        tier2 = thresholds.get("tier2_cutoff")
        tier3 = thresholds.get("tier3_cutoff")

        for field in ("score_range_min", "score_range_max", "auto_qualify_min", "tier1_cutoff", "tier2_cutoff", "tier3_cutoff"):
            if field in thresholds and not isinstance(thresholds[field], (int, float)):
                errors.append(f"thresholds.{field} must be numeric")

        if isinstance(score_min, (int, float)) and isinstance(score_max, (int, float)):
            if score_min >= score_max:
                errors.append("thresholds.score_range_min must be < thresholds.score_range_max")
        if isinstance(auto_q, (int, float)) and isinstance(score_min, (int, float)) and isinstance(score_max, (int, float)):
            if not (score_min <= auto_q <= score_max):
                errors.append("thresholds.auto_qualify_min must be within score range")
        if isinstance(tier1, (int, float)) and isinstance(tier2, (int, float)) and isinstance(tier3, (int, float)):
            if not (tier1 >= tier2 >= tier3):
                errors.append("thresholds tier cutoffs must satisfy tier1 >= tier2 >= tier3")

    return errors


REQUIRED_PROFILE_FIELDS = {"name", "identity_position", "track", "artist_statements"}


def validate_profiles() -> list[str]:
    """Validate profile JSON files have required fields and valid structure.

    Returns list of error strings.
    """
    import json

    from pipeline_lib import PROFILES_DIR

    errors = []
    if not PROFILES_DIR.exists():
        errors.append("Profile directory not found: targets/profiles/")
        return errors

    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        if "index" in profile_path.name:
            continue
        try:
            with open(profile_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"{profile_path.name}: invalid JSON — {e}")
            continue

        if not isinstance(data, dict):
            errors.append(f"{profile_path.name}: not a JSON object")
            continue

        for field in REQUIRED_PROFILE_FIELDS:
            if field not in data:
                errors.append(f"{profile_path.name}: missing required field '{field}'")

        # Validate artist_statements structure
        stmts = data.get("artist_statements")
        if isinstance(stmts, dict):
            for length_key in ("short", "medium", "long"):
                if length_key in stmts and not isinstance(stmts[length_key], str):
                    errors.append(f"{profile_path.name}: artist_statements.{length_key} must be a string")

    return errors


def validate_no_duplicate_urls(entries: list[dict], errors: list[str]) -> int:
    """Detect entries sharing the same target.application_url.

    Returns count of duplicates found.
    """
    url_map: dict[str, list[str]] = {}
    for entry in entries:
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        url = target.get("application_url", "")
        if not url or not isinstance(url, str):
            continue
        url_map.setdefault(url, []).append(entry.get("id", "unknown"))
    dupes = 0
    for url, ids in url_map.items():
        if len(ids) > 1:
            errors.append(f"Duplicate application_url '{url}' shared by: {', '.join(ids)}")
            dupes += 1
    return dupes


def validate_org_cap_warnings(entries: list[dict], warnings: list[str], cap: int = 1) -> int:
    """Flag orgs with more than `cap` active+submitted entries.

    Returns count of org-cap violations.
    """
    actionable_statuses = {"research", "qualified", "drafting", "staged", "submitted", "acknowledged", "interview"}
    org_map: dict[str, list[str]] = {}
    for entry in entries:
        status = entry.get("status", "")
        if status not in actionable_statuses:
            continue
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        org = target.get("organization", "")
        if not org or not isinstance(org, str):
            continue
        org_map.setdefault(org.lower(), []).append(entry.get("id", "unknown"))
    violations = 0
    for org, ids in sorted(org_map.items()):
        if len(ids) > cap:
            warnings.append(f"Org-cap violation: '{org}' has {len(ids)} entries (cap={cap}): {', '.join(ids)}")
            violations += 1
    return violations


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate pipeline YAML entries")
    parser.add_argument("--check-freshness", action="store_true",
                        help="Also check profile JSON freshness against metrics-snapshot.md")
    parser.add_argument("--check-profiles", action="store_true",
                        help="Also validate profile JSON schema")
    parser.add_argument("--check-id-maps", action="store_true",
                        help="Also validate PROFILE_ID_MAP and LEGACY_ID_MAP consistency")
    parser.add_argument("--check-rubric", action="store_true",
                        help="Also validate strategy/scoring-rubric.yaml")
    parser.add_argument("--check-org-cap", action="store_true",
                        help="Also check org-cap violations (>1 active+submitted per org)")
    parser.add_argument("--generate-id-maps", action="store_true",
                        help="Generate ID mapping suggestions at strategy/id-mappings.generated.yaml")
    args = parser.parse_args()

    all_errors = {}
    all_warnings: dict[str, list[str]] = {}
    file_count = 0
    seen_ids: dict[str, str] = {}  # id -> first filepath

    for pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            file_count += 1
            entry_warnings = []
            errors = validate_entry(filepath, warnings=entry_warnings)

            # Print non-fatal warnings
            for w in entry_warnings:
                all_warnings.setdefault(filepath.name, []).append(w)

            # Duplicate ID detection across all directories
            entry_id = filepath.stem
            if entry_id in seen_ids:
                errors.append(
                    f"Duplicate ID '{entry_id}' — also found at {seen_ids[entry_id]}"
                )
            else:
                seen_ids[entry_id] = str(filepath.relative_to(REPO_ROOT))

            if errors:
                all_errors[filepath.name] = errors

    if not file_count:
        print("No pipeline YAML files found.")
        sys.exit(1)

    has_errors = False

    if all_errors:
        print(f"VALIDATION FAILED — {len(all_errors)} file(s) with errors:\n")
        for filename, errors in all_errors.items():
            print(f"  {filename}:")
            for error in errors:
                print(f"    - {error}")
        print(f"\n{file_count} files checked, {len(all_errors)} with errors.")
        has_errors = True
    else:
        print(f"OK — {file_count} pipeline entries validated successfully.")

    if all_warnings:
        print(f"\nWarnings ({sum(len(v) for v in all_warnings.values())}):")
        for filename, warns in all_warnings.items():
            for w in warns:
                print(f"  {filename}: {w}")

    if args.check_freshness:
        print()
        freshness_warnings = check_profile_freshness()
        for w in freshness_warnings:
            print(w)
        stale = any("STALE" in w for w in freshness_warnings)
        if stale:
            has_errors = True

    if args.check_profiles:
        print()
        profile_errors = validate_profiles()
        if profile_errors:
            print(f"PROFILE VALIDATION — {len(profile_errors)} issue(s):\n")
            for e in profile_errors:
                print(f"  - {e}")
            has_errors = True
        else:
            print("Profile validation OK — all profiles have required fields.")

    if args.check_id_maps:
        print()
        id_errors = validate_id_mappings()
        if id_errors:
            print(f"ID MAPPING VALIDATION — {len(id_errors)} issue(s):\n")
            for e in id_errors:
                print(f"  - {e}")
            has_errors = True
        else:
            print("ID mapping validation OK — all maps consistent with filesystem.")

    if args.check_rubric:
        print()
        rubric_errors = validate_scoring_rubric()
        if rubric_errors:
            print(f"SCORING RUBRIC VALIDATION — {len(rubric_errors)} issue(s):\n")
            for e in rubric_errors:
                print(f"  - {e}")
            has_errors = True
        else:
            print("Scoring rubric validation OK — weights and thresholds are consistent.")

    if args.check_org_cap:
        print()
        # Load all entries for cross-entry checks
        all_entries = []
        for pipeline_dir in PIPELINE_DIRS:
            if not pipeline_dir.exists():
                continue
            for filepath in sorted(pipeline_dir.glob("*.yaml")):
                if filepath.name.startswith("_"):
                    continue
                try:
                    with open(filepath) as f:
                        entry_data = load_yaml_strict(f.read())
                    if isinstance(entry_data, dict):
                        all_entries.append(entry_data)
                except yaml.YAMLError:
                    continue
        # Duplicate URL check
        url_errors = []
        validate_no_duplicate_urls(all_entries, url_errors)
        if url_errors:
            print(f"DUPLICATE URL CHECK — {len(url_errors)} issue(s):")
            for e in url_errors:
                print(f"  - {e}")
            has_errors = True
        else:
            print("Duplicate URL check OK — no shared application URLs.")
        # Org-cap check
        org_warnings = []
        violations = validate_org_cap_warnings(all_entries, org_warnings)
        if org_warnings:
            print(f"\nORG-CAP WARNINGS — {violations} violation(s):")
            for w in org_warnings:
                print(f"  - {w}")
        else:
            print("Org-cap check OK — no violations.")

    if args.generate_id_maps:
        print()
        try:
            from generate_id_mappings import OUTPUT_PATH, generate_legacy_map, generate_profile_map

            payload = {
                "generated": OUTPUT_PATH.name,
                "profile_id_map": generate_profile_map(),
                "legacy_id_map": generate_legacy_map(),
            }
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True))
            print(f"Generated ID map suggestions: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
        except Exception as exc:
            print(f"ID mapping generation failed: {exc}")
            has_errors = True

    if has_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
