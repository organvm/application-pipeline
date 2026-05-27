"""Freshness and era utilities for pipeline entries."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypeAlias

from pipeline_entry_state import parse_date as _parse_date
from pipeline_market import build_market_intelligence_loader

REPO_ROOT = Path(__file__).resolve().parent.parent
(
    load_market_intelligence,
    _get_portal_scores,
    _get_strategic_base,
    _portal_scores_default,
    _strategic_base_default,
) = build_market_intelligence_loader(REPO_ROOT)

PRECISION_PIVOT_DATE = "2026-03-04"

# Job posting freshness thresholds (hours)
JOB_FRESH_HOURS = 24
JOB_WARM_HOURS = 48
JOB_STALE_HOURS = 72


PIPELINE_DIR_ACTIVE = REPO_ROOT / "pipeline" / "active"
PIPELINE_DIR_RESEARCH_POOL = REPO_ROOT / "pipeline" / "research_pool"

DateLike: TypeAlias = str | date | datetime | None
EntryData: TypeAlias = dict[str, object]


def flush_stale_active_jobs(*, quiet: bool = False) -> int:
    """Move job-track entries in active/ older than 72h to research_pool/.

    Called automatically by morning.py and standup.py before rendering output
    so the user only ever sees hot leads.

    Set PIPELINE_NO_MUTATE=1 to disable the on-disk move (used by tests that
    invoke standup/morning as subprocesses, so the suite never mutates the real
    pipeline tree).

    Returns the number of entries flushed.
    """
    import os

    import yaml

    if os.environ.get("PIPELINE_NO_MUTATE"):
        return 0

    _, _, stale_hours = _load_freshness_thresholds()
    flushed = 0

    for filepath in sorted(PIPELINE_DIR_ACTIVE.glob("*.yaml")):
        try:
            data = yaml.safe_load(filepath.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        track = data.get("track", "")
        if track != "job":
            continue  # freshness is a job-track concept (matches get_freshness_tier/compute_freshness_score)

        if data.get("status") == "deferred":
            continue

        age = get_posting_age_hours(data)
        if age is None or age <= stale_hours:
            continue

        dest = PIPELINE_DIR_RESEARCH_POOL / filepath.name
        if dest.exists():
            filepath.unlink()
        else:
            # Reset status to research before moving
            data["status"] = "research"
            filepath.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
            filepath.rename(dest)
        flushed += 1

    if flushed and not quiet:
        print(f"  [freshness] Flushed {flushed} stale job entries from active/ → research_pool/")

    return flushed


def get_entry_era(entry: EntryData) -> str:
    """Derive 'volume' or 'precision' from timeline.submitted and pivot date."""
    timeline = entry.get("timeline", {})
    if not isinstance(timeline, dict):
        return "precision"
    submitted_str = timeline.get("submitted")
    if not submitted_str:
        return "precision"
    submitted_str = str(submitted_str).strip().strip('"')
    try:
        submitted_date = date.fromisoformat(submitted_str)
        pivot_date = date.fromisoformat(PRECISION_PIVOT_DATE)
        return "volume" if submitted_date < pivot_date else "precision"
    except (ValueError, TypeError):
        return "precision"


def _load_freshness_thresholds() -> tuple[float, float, float]:
    """Load job freshness thresholds from market intelligence."""
    intel = load_market_intelligence()
    thresholds = intel.get("job_posting_freshness_hours", {})
    if not isinstance(thresholds, dict):
        return float(JOB_FRESH_HOURS), float(JOB_WARM_HOURS), float(JOB_STALE_HOURS)
    fresh = thresholds.get("fresh", JOB_FRESH_HOURS)
    warm = thresholds.get("warm", JOB_WARM_HOURS)
    stale = thresholds.get("stale", JOB_STALE_HOURS)
    try:
        return float(fresh), float(warm), float(stale)
    except (TypeError, ValueError):
        return float(JOB_FRESH_HOURS), float(JOB_WARM_HOURS), float(JOB_STALE_HOURS)


def _parse_datetime_aware(date_str: DateLike) -> datetime | None:
    """Parse date/datetime values into timezone-aware UTC datetimes."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        if date_str.tzinfo is None:
            return date_str.replace(tzinfo=UTC)
        return date_str
    if isinstance(date_str, date):
        return datetime(date_str.year, date_str.month, date_str.day, tzinfo=UTC)
    value = str(date_str).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            continue
    return None


def get_posting_age_hours(entry: EntryData) -> float | None:
    """Compute posting age in hours using timeline/posting-related fields."""

    def _is_date_only(raw_value: DateLike) -> bool:
        if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
            return True
        if isinstance(raw_value, str):
            return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value.strip()))
        return False

    def _hours_from_date_only(raw_value: DateLike) -> float | None:
        parsed = _parse_date(raw_value)
        if parsed is None:
            return None
        return float((date.today() - parsed).days * 24)

    timeline = entry.get("timeline", {})
    if not isinstance(timeline, dict):
        timeline = {}

    parsed_dt = None
    for field in ("posting_date", "discovered", "date_added"):
        raw_value = timeline.get(field)
        if _is_date_only(raw_value):
            return _hours_from_date_only(raw_value)
        parsed_dt = _parse_datetime_aware(raw_value)
        if parsed_dt is not None:
            break

    if parsed_dt is None:
        raw_value = entry.get("last_touched")
        if _is_date_only(raw_value):
            return _hours_from_date_only(raw_value)
        parsed_dt = _parse_datetime_aware(raw_value)

    if parsed_dt is None:
        return None

    delta = datetime.now(UTC) - parsed_dt
    return delta.total_seconds() / 3600.0


def get_freshness_tier(entry: EntryData) -> str | None:
    """Return one of hot/warm/cooling/stale for job entries."""
    if entry.get("track") != "job":
        return None

    age = get_posting_age_hours(entry)
    if age is None:
        return None

    fresh, warm, stale = _load_freshness_thresholds()
    if age < fresh:
        return "hot"
    if age < warm:
        return "warm"
    if age < stale:
        return "cooling"
    return "stale"


def compute_freshness_score(entry: EntryData) -> float:
    """Return a 0.0-1.0 linear freshness decay multiplier for job entries."""
    if entry.get("track") != "job":
        return 1.0

    age = get_posting_age_hours(entry)
    if age is None:
        return 0.0

    _, _, stale = _load_freshness_thresholds()
    if stale <= 0:
        return 0.0

    score = 1.0 - (age / stale)
    return max(0.0, min(1.0, score))
