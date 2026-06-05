#!/usr/bin/env python3
"""Programmatic API layer for pipeline operations.

Provides typed, non-interactive wrappers around core script logic for use by
CLI and MCP surfaces.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

import yaml

try:  # Prefer package-style imports when available.
    from .advance import advance_entry as _advance_file_entry
    from .advance import can_advance
    from .compose import compose as compose_document
    from .compose import find_entry as find_compose_entry
    from .draft import assemble_draft, populate_portal_fields
    from .enrich import detect_gaps as _detect_gaps
    from .followup import collect_due_actions as _collect_due_actions
    from .followup import get_submitted_entries as _get_submitted_entries
    from .hygiene import check_gate as _check_gate
    from .hygiene import check_stale_rolling as _check_stale_rolling
    from .pipeline_lib import (
        ALL_PIPELINE_DIRS,
        DRAFTS_DIR,
        SUBMISSIONS_DIR,
        VALID_STATUSES,
        VALID_TRACKS,
        count_words,
        load_entry_by_id,
        load_profile,
    )
    from .pipeline_lib import (
        load_entries as load_all_entries,
    )
    from .score import (
        ALL_PIPELINE_DIRS_WITH_POOL,
        _load_entries_raw,
        compute_composite,
        compute_dimensions,
        run_auto_qualify,
        update_entry_file,
    )
    from .score import (
        load_entries as load_score_entries,
    )
    from .submit import generate_checklist as _generate_checklist
    from .triage import generate_triage_data as _generate_triage_data
    from .validate import PIPELINE_DIRS, REQUIRED_FIELDS
    from .validate import validate_entry as validate_file_entry
except ImportError:  # pragma: no cover - script execution fallback
    from advance import advance_entry as _advance_file_entry
    from advance import can_advance
    from compose import compose as compose_document
    from compose import find_entry as find_compose_entry
    from draft import assemble_draft, populate_portal_fields
    from enrich import detect_gaps as _detect_gaps
    from followup import collect_due_actions as _collect_due_actions
    from followup import get_submitted_entries as _get_submitted_entries
    from hygiene import check_gate as _check_gate
    from hygiene import check_stale_rolling as _check_stale_rolling
    from pipeline_lib import (
        ALL_PIPELINE_DIRS,
        DRAFTS_DIR,
        SUBMISSIONS_DIR,
        VALID_STATUSES,
        VALID_TRACKS,
        count_words,
        load_entry_by_id,
        load_profile,
    )
    from pipeline_lib import (
        load_entries as load_all_entries,
    )
    from score import (
        ALL_PIPELINE_DIRS_WITH_POOL,
        _load_entries_raw,
        compute_composite,
        compute_dimensions,
        run_auto_qualify,
        update_entry_file,
    )
    from score import (
        load_entries as load_score_entries,
    )
    from submit import generate_checklist as _generate_checklist
    from triage import generate_triage_data as _generate_triage_data
    from validate import PIPELINE_DIRS, REQUIRED_FIELDS
    from validate import validate_entry as validate_file_entry


class ResultStatus(Enum):
    """Result status indicators."""

    SUCCESS = "success"
    ERROR = "error"
    DRY_RUN = "dry_run"
    NO_CHANGE = "no_change"


@dataclass
class ScoreResult:
    """Result of scoring an entry or batch."""

    status: ResultStatus
    entry_id: str
    old_score: float | None = None
    new_score: float | None = None
    dimensions: dict[str, int] | None = None
    message: str = ""
    error: str | None = None


@dataclass
class AdvanceResult:
    """Result of advancing an entry."""

    status: ResultStatus
    entry_id: str
    old_status: str | None = None
    new_status: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class DraftResult:
    """Result of drafting an entry."""

    status: ResultStatus
    entry_id: str
    content: str | None = None
    file_path: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class ComposeResult:
    """Result of composing an entry."""

    status: ResultStatus
    entry_id: str
    content: str | None = None
    file_path: str | None = None
    word_count: int | None = None
    block_sources: list[str] | None = None
    message: str = ""
    error: str | None = None


@dataclass
class ValidationResult:
    """Result of validating one or more entries."""

    status: ResultStatus
    entry_id: str
    is_valid: bool = False
    errors: list[str] | None = None
    warnings: list[str] | None = None
    message: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


_NATURAL_NEXT_STATUS: dict[str, str] = {
    "research": "qualified",
    "qualified": "drafting",
    "drafting": "staged",
    "staged": "submitted",
    "deferred": "qualified",
    "submitted": "acknowledged",
    "acknowledged": "interview",
    "interview": "outcome",
}

API_OPERATION_ERRORS = (
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    KeyError,
    json.JSONDecodeError,
    yaml.YAMLError,
)


def _natural_next_status(current_status: str) -> str | None:
    """Return the conventional next status for a status, if defined."""

    return _NATURAL_NEXT_STATUS.get(current_status)


def score_entry(
    entry_id: str | None,
    auto_qualify: bool = False,
    dry_run: bool = True,
    min_score: float = 7.0,
    limit: int = 0,
    verbose: bool = False,
    all_entries: bool = False,
) -> ScoreResult:
    """Score one entry, all entries, or run auto-qualify."""

    try:
        if auto_qualify and all_entries:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id="batch",
                error="auto_qualify and all_entries are mutually exclusive",
            )

        if auto_qualify:
            capture = io.StringIO()
            with redirect_stdout(capture):
                run_auto_qualify(
                    dry_run=dry_run,
                    yes=not dry_run,
                    min_score=min_score,
                    limit=limit,
                )
            output = capture.getvalue().strip()
            summary = output.splitlines()[-1] if output else "auto-qualify complete"
            return ScoreResult(
                status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
                entry_id="batch",
                message=summary,
            )

        if all_entries:
            entries = load_score_entries(entry_id=None, include_pool=False)
            if not entries:
                return ScoreResult(
                    status=ResultStatus.ERROR,
                    entry_id="batch",
                    error="no entries found",
                )
            all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
            updated = 0
            for filepath, data in entries:
                dims = compute_dimensions(data, all_raw)
                composite = compute_composite(dims, data.get("track", ""))
                update_entry_file(filepath, dims, composite, dry_run=dry_run)
                updated += 1
            return ScoreResult(
                status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
                entry_id="batch",
                message=f"scored {updated} entries" + (" (dry-run)" if dry_run else ""),
            )

        if not entry_id:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required for single scoring",
            )

        entries = load_score_entries(entry_id=entry_id, include_pool=False)
        if not entries:
            return ScoreResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        filepath, data = entries[0]
        all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
        dimensions = compute_dimensions(data, all_raw)
        composite = compute_composite(dimensions, data.get("track", ""))
        old_score, new_score = update_entry_file(filepath, dimensions, composite, dry_run=dry_run)

        delta = ""
        if old_score is not None:
            delta = f" (was {old_score}, delta {new_score - old_score:+.1f})"

        message = f"score={new_score}{delta}" if not verbose else f"score={new_score}, dims={dimensions}"
        return ScoreResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            old_score=old_score,
            new_score=new_score,
            dimensions=dimensions,
            message=message,
        )
    except API_OPERATION_ERRORS as exc:
        return ScoreResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "",
            error=f"{type(exc).__name__}: {exc}",
        )


def advance_entry(
    entry_id: str,
    to_status: str | None = None,
    dry_run: bool = True,
) -> AdvanceResult:
    """Advance an entry to the next status (or specified status)."""

    try:
        if not entry_id:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        filepath, data = load_entry_by_id(entry_id)
        if not filepath or not data:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        old_status = str(data.get("status", ""))
        if not old_status:
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error="entry missing status",
            )

        target_status = to_status or _natural_next_status(old_status)
        if not target_status:
            return AdvanceResult(
                status=ResultStatus.NO_CHANGE,
                entry_id=entry_id,
                old_status=old_status,
                message=f"no natural next status from '{old_status}'",
            )

        if not can_advance(old_status, target_status):
            return AdvanceResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                old_status=old_status,
                new_status=target_status,
                error=f"invalid transition: {old_status} -> {target_status}",
            )

        if dry_run:
            return AdvanceResult(
                status=ResultStatus.DRY_RUN,
                entry_id=entry_id,
                old_status=old_status,
                new_status=target_status,
                message=f"would advance {old_status} -> {target_status}",
            )

        _advance_file_entry(filepath, entry_id, target_status)
        return AdvanceResult(
            status=ResultStatus.SUCCESS,
            entry_id=entry_id,
            old_status=old_status,
            new_status=target_status,
            message=f"advanced {old_status} -> {target_status}",
        )
    except API_OPERATION_ERRORS as exc:
        return AdvanceResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def _resolve_profile(entry_id: str) -> dict | None:
    """Resolve profile by entry id using canonical loader and target_id fallback."""

    profile = load_profile(entry_id)
    if profile:
        return profile

    profiles_dir = Path(__file__).resolve().parent.parent / "targets" / "profiles"
    if not profiles_dir.exists():
        return None

    for profile_path in profiles_dir.glob("*.json"):
        try:
            pdata = json.loads(profile_path.read_text())
        except json.JSONDecodeError:
            continue
        if pdata.get("target_id") == entry_id:
            return pdata
    return None


def draft_entry(
    entry_id: str,
    profile: bool = False,
    length: str = "medium",
    populate: bool = False,
    dry_run: bool = True,
) -> DraftResult:
    """Draft application materials from profile or blocks."""

    try:
        if not entry_id:
            return DraftResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        filepath, entry = load_entry_by_id(entry_id)
        if not entry:
            return DraftResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        # Draft assembly is profile-driven; always resolve profile when available.
        profile_data = _resolve_profile(entry_id)
        document, warnings = assemble_draft(entry, profile_data, length)

        file_path = None
        if not dry_run:
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DRAFTS_DIR / f"{entry_id}.md"
            output_path.write_text(document)
            file_path = str(output_path)

            if populate and profile_data and filepath:
                populate_portal_fields(filepath, entry, profile_data)

        warning_msg = f" ({len(warnings)} warnings)" if warnings else ""
        return DraftResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            content=document,
            file_path=file_path,
            message=f"draft generated{warning_msg}",
        )
    except API_OPERATION_ERRORS as exc:
        return DraftResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def compose_entry(
    entry_id: str,
    snapshot: bool = False,
    counts: bool = False,
    profile: bool = False,
    dry_run: bool = True,
) -> ComposeResult:
    """Compose submission from blocks and materials."""

    try:
        if not entry_id:
            return ComposeResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        entry = find_compose_entry(entry_id)
        if not entry:
            return ComposeResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        profile_data = _resolve_profile(entry_id) if profile else None
        content = compose_document(entry, profile_data, ai_smooth=False)
        word_count = count_words(content)

        file_path = None
        if snapshot and not dry_run:
            SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
            snapshot_name = f"{entry_id}-{date.today().isoformat()}.md"
            snapshot_path = SUBMISSIONS_DIR / snapshot_name
            snapshot_path.write_text(content)
            file_path = str(snapshot_path)

        submission = entry.get("submission", {}) if isinstance(entry.get("submission"), dict) else {}
        block_sources = []
        blocks_used = submission.get("blocks_used")
        if isinstance(blocks_used, dict):
            block_sources = [str(v) for v in blocks_used.values()]

        message = f"composed {word_count} words"
        if counts:
            message += f" (counts requested: {word_count}w)"

        return ComposeResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            content=content,
            file_path=file_path,
            word_count=word_count,
            block_sources=block_sources,
            message=message,
        )
    except API_OPERATION_ERRORS as exc:
        return ComposeResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


def _validate_inline_entry(entry_dict: dict) -> tuple[list[str], list[str]]:
    """Validate inline entry dict using core structural checks."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(entry_dict, dict):
        return ["entry_dict must be a mapping"], warnings

    missing = sorted(REQUIRED_FIELDS - set(entry_dict.keys()))
    for field in missing:
        errors.append(f"Missing required field: {field}")

    track = entry_dict.get("track")
    if track and track not in VALID_TRACKS:
        errors.append(f"Invalid track: '{track}'")

    status = entry_dict.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status: '{status}'")

    return errors, warnings


def validate_entry(
    entry_id: str | None = None,
    entry_dict: dict | None = None,
) -> ValidationResult:
    """Validate a single entry, an inline entry dict, or the full pipeline."""

    try:
        if entry_dict is not None:
            errors, warnings = _validate_inline_entry(entry_dict)
            is_valid = len(errors) == 0
            return ValidationResult(
                status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
                entry_id=str(entry_dict.get("id", "inline")),
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="validation passed" if is_valid else "validation failed",
                error="; ".join(errors) if errors else None,
            )

        if entry_id:
            filepath, _ = load_entry_by_id(entry_id)
            if not filepath:
                return ValidationResult(
                    status=ResultStatus.ERROR,
                    entry_id=entry_id,
                    is_valid=False,
                    errors=[f"entry '{entry_id}' not found"],
                    message="validation failed",
                    error=f"entry '{entry_id}' not found",
                )
            warnings: list[str] = []
            errors = validate_file_entry(filepath, warnings=warnings)
            is_valid = len(errors) == 0
            return ValidationResult(
                status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
                entry_id=entry_id,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="validation passed" if is_valid else "validation failed",
                error="; ".join(errors) if errors else None,
            )

        # Full pipeline validation
        all_errors: list[str] = []
        all_warnings: list[str] = []
        file_count = 0

        for pipeline_dir in PIPELINE_DIRS:
            if not pipeline_dir.exists():
                continue
            for filepath in sorted(pipeline_dir.glob("*.yaml")):
                if filepath.name.startswith("_"):
                    continue
                file_count += 1
                warnings: list[str] = []
                errors = validate_file_entry(filepath, warnings=warnings)
                all_warnings.extend([f"{filepath.name}: {w}" for w in warnings])
                all_errors.extend([f"{filepath.name}: {e}" for e in errors])

        if file_count == 0:
            return ValidationResult(
                status=ResultStatus.ERROR,
                entry_id="all",
                is_valid=False,
                errors=["No pipeline YAML files found"],
                message="validation failed",
                error="No pipeline YAML files found",
            )

        is_valid = len(all_errors) == 0
        return ValidationResult(
            status=ResultStatus.SUCCESS if is_valid else ResultStatus.ERROR,
            entry_id="all",
            is_valid=is_valid,
            errors=all_errors,
            warnings=all_warnings,
            message=f"validated {file_count} entries",
            error="; ".join(all_errors[:3]) if all_errors else None,
        )
    except API_OPERATION_ERRORS as exc:
        return ValidationResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "all",
            is_valid=False,
            errors=[f"{type(exc).__name__}: {exc}"],
            message="validation failed",
            error=f"{type(exc).__name__}: {exc}",
        )


# ============================================================================
# EXPANDED API OPERATIONS
# ============================================================================


@dataclass
class EnrichResult:
    """Result of enrichment gap analysis or enrichment execution."""

    status: ResultStatus
    entry_id: str
    gaps: list[str] | None = None
    message: str = ""
    error: str | None = None


@dataclass
class FollowupResult:
    """Result of follow-up action collection."""

    status: ResultStatus
    entry_id: str
    due_actions: list[dict] | None = None
    total_entries: int = 0
    message: str = ""
    error: str | None = None


@dataclass
class HygieneResult:
    """Result of hygiene checks on entries."""

    status: ResultStatus
    entry_id: str
    gate_issues: list[str] | None = None
    stale_entries: list[dict] | None = None
    total_issues: int = 0
    message: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if self.gate_issues is None:
            self.gate_issues = []
        if self.stale_entries is None:
            self.stale_entries = []


@dataclass
class StandupResult:
    """Result of standup data collection."""

    status: ResultStatus
    entry_id: str
    output: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class TriageResult:
    """Result of triage analysis."""

    status: ResultStatus
    entry_id: str
    staged_demotions: list[dict] | None = None
    org_cap_deferrals: list[dict] | None = None
    summary: dict | None = None
    message: str = ""
    error: str | None = None


@dataclass
class SubmitResult:
    """Result of submission checklist generation."""

    status: ResultStatus
    entry_id: str
    checklist: str | None = None
    issues: list[str] | None = None
    message: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []


@dataclass
class PrecedentRegistryResult:
    """Result of loading the domain-surfaces / precedent-processes registry."""

    status: ResultStatus
    version: str | None = None
    description: str | None = None
    precedents: dict | None = None
    boundary_conditions: list[str] | None = None
    domains: dict | None = None
    message: str = ""
    error: str | None = None


def enrich_entry(
    entry_id: str | None = None,
    all_entries: bool = False,
) -> EnrichResult:
    """Analyze enrichment gaps for one entry or all entries.

    This is a read-only gap analysis — it does not modify files.
    """
    try:
        if not entry_id and not all_entries:
            return EnrichResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id or all_entries required",
            )

        entries = load_all_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)

        if entry_id:
            matched = [e for e in entries if e.get("id") == entry_id]
            if not matched:
                return EnrichResult(
                    status=ResultStatus.ERROR,
                    entry_id=entry_id,
                    error=f"entry '{entry_id}' not found",
                )
            gaps = _detect_gaps(matched[0])
            return EnrichResult(
                status=ResultStatus.SUCCESS,
                entry_id=entry_id,
                gaps=gaps,
                message=f"{len(gaps)} gaps found" if gaps else "fully enriched",
            )

        # All entries
        total_gaps = 0
        entries_with_gaps = 0
        for entry in entries:
            gaps = _detect_gaps(entry)
            if gaps:
                entries_with_gaps += 1
                total_gaps += len(gaps)

        return EnrichResult(
            status=ResultStatus.SUCCESS,
            entry_id="batch",
            gaps=[],
            message=f"{entries_with_gaps} entries with {total_gaps} total gaps",
        )
    except API_OPERATION_ERRORS as exc:
        return EnrichResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "batch",
            error=f"{type(exc).__name__}: {exc}",
        )


def followup_data(
    entry_id: str | None = None,
) -> FollowupResult:
    """Collect due follow-up actions for submitted entries."""
    try:
        entries = _get_submitted_entries()

        if entry_id:
            entries = [e for e in entries if e.get("id") == entry_id]
            if not entries:
                return FollowupResult(
                    status=ResultStatus.ERROR,
                    entry_id=entry_id,
                    error=f"no submitted entry '{entry_id}' found",
                )

        actions = _collect_due_actions(entries)
        eid = entry_id or "all"
        return FollowupResult(
            status=ResultStatus.SUCCESS,
            entry_id=eid,
            due_actions=actions,
            total_entries=len(entries),
            message=f"{len(actions)} due actions across {len(entries)} entries",
        )
    except API_OPERATION_ERRORS as exc:
        return FollowupResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "all",
            error=f"{type(exc).__name__}: {exc}",
        )


def hygiene_check(
    entry_id: str | None = None,
) -> HygieneResult:
    """Run hygiene gate checks on one entry or all entries."""
    try:
        if entry_id:
            filepath, data = load_entry_by_id(entry_id)
            if not data:
                return HygieneResult(
                    status=ResultStatus.ERROR,
                    entry_id=entry_id,
                    error=f"entry '{entry_id}' not found",
                )
            issues = _check_gate(data)
            return HygieneResult(
                status=ResultStatus.SUCCESS,
                entry_id=entry_id,
                gate_issues=issues,
                total_issues=len(issues),
                message="clean" if not issues else f"{len(issues)} gate issues",
            )

        # All entries
        entries = load_all_entries(dirs=ALL_PIPELINE_DIRS)
        all_issues: list[str] = []
        for entry in entries:
            issues = _check_gate(entry)
            for issue in issues:
                all_issues.append(f"{entry.get('id', '?')}: {issue}")

        stale = _check_stale_rolling(entries)
        total = len(all_issues) + len(stale)

        return HygieneResult(
            status=ResultStatus.SUCCESS,
            entry_id="all",
            gate_issues=all_issues,
            stale_entries=stale,
            total_issues=total,
            message=f"{total} issues ({len(all_issues)} gate, {len(stale)} stale)",
        )
    except API_OPERATION_ERRORS as exc:
        return HygieneResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "all",
            error=f"{type(exc).__name__}: {exc}",
        )


def standup_data(
    hours: float = 3.0,
    section: str | None = None,
) -> StandupResult:
    """Capture standup output as a string."""
    try:
        from contextlib import redirect_stdout as _redirect

        capture = io.StringIO()
        # Import here to avoid circular dependency at module level.
        try:
            from .standup import run_standup as _run_standup
        except ImportError:  # pragma: no cover
            from standup import run_standup as _run_standup

        with _redirect(capture):
            _run_standup(hours, section, do_log=False)

        output = capture.getvalue()
        return StandupResult(
            status=ResultStatus.SUCCESS,
            entry_id="standup",
            output=output,
            message=f"standup captured ({len(output)} chars)",
        )
    except API_OPERATION_ERRORS as exc:
        return StandupResult(
            status=ResultStatus.ERROR,
            entry_id="standup",
            error=f"{type(exc).__name__}: {exc}",
        )


def triage_data(
    min_score: float = 9.0,
    dry_run: bool = True,
) -> TriageResult:
    """Run triage analysis on the pipeline."""
    try:
        entries = load_all_entries(dirs=ALL_PIPELINE_DIRS)
        data = _generate_triage_data(entries, min_score=min_score, dry_run=dry_run)

        return TriageResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id="triage",
            staged_demotions=data["staged_demotions"],
            org_cap_deferrals=data["org_cap_deferrals"],
            summary=data["summary"],
            message=f"{data['summary']['staged_below_threshold']} staged demotions, "
            f"{data['summary']['org_cap_violations']} org-cap deferrals",
        )
    except API_OPERATION_ERRORS as exc:
        return TriageResult(
            status=ResultStatus.ERROR,
            entry_id="triage",
            error=f"{type(exc).__name__}: {exc}",
        )


def submit_entry(
    entry_id: str,
    dry_run: bool = True,
) -> SubmitResult:
    """Generate a submission checklist for an entry."""
    try:
        if not entry_id:
            return SubmitResult(
                status=ResultStatus.ERROR,
                entry_id="",
                error="entry_id required",
            )

        filepath, entry = load_entry_by_id(entry_id)
        if not entry:
            return SubmitResult(
                status=ResultStatus.ERROR,
                entry_id=entry_id,
                error=f"entry '{entry_id}' not found",
            )

        profile = _resolve_profile(entry_id)

        # Legacy script lookup (best-effort)
        legacy = None
        try:
            try:
                from .pipeline_lib import load_legacy_script
            except ImportError:  # pragma: no cover
                from pipeline_lib import load_legacy_script
            legacy = load_legacy_script(entry_id)
        except Exception:
            pass

        checklist, issues = _generate_checklist(entry, profile, legacy)

        return SubmitResult(
            status=ResultStatus.DRY_RUN if dry_run else ResultStatus.SUCCESS,
            entry_id=entry_id,
            checklist=checklist,
            issues=issues,
            message=f"checklist generated ({len(issues)} issues)" if issues else "checklist ready",
        )
    except API_OPERATION_ERRORS as exc:
        return SubmitResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id,
            error=f"{type(exc).__name__}: {exc}",
        )


# Canonical location of the precedent-processes / domain-surfaces registry.
PRECEDENT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "strategy" / "domain-surfaces-registry.yaml"

VALID_PRECEDENT_DOMAINS = ("academic", "market", "engineering")


def load_precedent_registry(
    domain: str | None = None,
    registry_path: Path | None = None,
) -> PrecedentRegistryResult:
    """Load the domain-surfaces registry that names the product's precedent processes.

    Shared loader behind the REST and MCP surfaces — neither parses the YAML
    directly. Returns the registry's ``version``, ``precedents``,
    ``boundary_conditions``, and ``domains``. When ``domain`` is given, ``domains``
    is narrowed to that single domain's instances; an unknown domain is a clean
    error, and a missing/unreadable registry file is reported structurally rather
    than raised.
    """

    path = registry_path or PRECEDENT_REGISTRY_PATH
    try:
        if not path.exists():
            return PrecedentRegistryResult(
                status=ResultStatus.ERROR,
                error=f"registry not found: {path}",
                message="precedent registry unavailable",
            )

        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            return PrecedentRegistryResult(
                status=ResultStatus.ERROR,
                error=f"registry is not a mapping: {path}",
                message="precedent registry malformed",
            )

        all_domains = data.get("domains") or {}
        if domain is not None:
            if domain not in all_domains:
                known = ", ".join(sorted(all_domains)) or "(none)"
                return PrecedentRegistryResult(
                    status=ResultStatus.ERROR,
                    error=f"unknown domain '{domain}' (known: {known})",
                    message="unknown precedent domain",
                )
            domains = {domain: all_domains[domain]}
        else:
            domains = all_domains

        return PrecedentRegistryResult(
            status=ResultStatus.SUCCESS,
            version=data.get("version"),
            description=data.get("description"),
            precedents=data.get("precedents") or {},
            boundary_conditions=data.get("boundary_conditions") or [],
            domains=domains,
            message=(
                f"loaded domain '{domain}'"
                if domain is not None
                else f"loaded {len(domains)} domains"
            ),
        )
    except API_OPERATION_ERRORS as exc:
        return PrecedentRegistryResult(
            status=ResultStatus.ERROR,
            error=f"{type(exc).__name__}: {exc}",
            message="precedent registry load failed",
        )


__all__ = [
    "ResultStatus",
    "ScoreResult",
    "AdvanceResult",
    "DraftResult",
    "ComposeResult",
    "ValidationResult",
    "EnrichResult",
    "FollowupResult",
    "HygieneResult",
    "StandupResult",
    "TriageResult",
    "SubmitResult",
    "PrecedentRegistryResult",
    "score_entry",
    "advance_entry",
    "draft_entry",
    "compose_entry",
    "validate_entry",
    "enrich_entry",
    "followup_data",
    "hygiene_check",
    "standup_data",
    "triage_data",
    "submit_entry",
    "load_precedent_registry",
]
