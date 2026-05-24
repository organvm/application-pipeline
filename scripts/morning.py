#!/usr/bin/env python3
"""Morning autopilot: unified morning digest combining health, stale, followup, campaign, funding.

Replaces the 4-command morning sequence (standup → followup → outcomes → campaign)
with a single invocation that produces a unified brief.

Usage:
    python scripts/morning.py                # Full morning digest
    python scripts/morning.py --brief        # Top action only (one line)
    python scripts/morning.py --save         # Save digest to signals/
"""

import argparse
import io
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    SIGNALS_DIR,
    load_entries,
)


def capture_output(fn, *args, **kwargs):
    """Call fn and capture its stdout, returning (result, output_text)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def get_health(entries: list[dict]) -> tuple[dict, str]:
    """Run section_health and capture output + return dict."""
    from standup import section_health
    return capture_output(section_health, entries)


def get_stale(entries: list[dict]) -> tuple[dict, str]:
    """Run section_stale and capture output + return dict."""
    from standup import section_stale
    return capture_output(section_stale, entries)


def get_followup(entries: list[dict]) -> tuple[None, str]:
    """Run section_followup and capture output."""
    from standup import section_followup
    return capture_output(section_followup, entries)


def get_campaign(entries: list[dict], days_ahead: int = 14) -> str:
    """Get formatted campaign view."""
    from campaign import format_campaign_view, get_campaign_entries
    campaign_entries = get_campaign_entries(entries, days_ahead)
    return format_campaign_view(campaign_entries, days_ahead)


def get_funding() -> tuple[None, str]:
    """Run section_funding and capture output."""
    from standup import section_funding
    return capture_output(section_funding)


def get_blind_spot_progress() -> str:
    """Get blind spot progress bar summary."""
    try:
        from blind_spot_tracker import compute_progress, get_blind_spots
        spots = get_blind_spots()
        progress = compute_progress(spots)
        return f"Blind spots: {progress['bar']} ({progress['pct']}%)"
    except Exception:
        return ""


def get_freshness_summary(entries: list[dict]) -> str:
    """Get entry freshness summary."""
    try:
        from freshness_monitor import compute_freshness_report
        report = compute_freshness_report(entries)
        stale_n = len(report.get("stale", []))
        expired_n = len(report.get("expired", []))
        if stale_n + expired_n > 0:
            parts = []
            if stale_n:
                parts.append(f"{stale_n} stale postings")
            if expired_n:
                parts.append(f"{expired_n} expired postings")
            return f"Freshness: {' | '.join(parts)}"
        return ""
    except Exception:
        return ""


def compute_top_action(
    health: dict,
    stale: dict,
    campaign_text: str,
    followup_text: str,
) -> str:
    """Determine the single most important action for today.

    Priority order:
    1. Critical campaign entries (deadline ≤3d)
    2. Overdue follow-ups
    3. Expired entries needing archival
    4. At-risk entries needing advancement
    5. Stagnant entries needing review
    6. General pipeline work
    """
    # Check for critical items in campaign
    if "CRITICAL:" in campaign_text:
        critical_section = campaign_text.split("CRITICAL:")[1].split("\n")
        for line in critical_section:
            line = line.strip()
            if line and line != "(none)" and not line.startswith("URGENT"):
                return f"CRITICAL DEADLINE: {line.strip()[:80]}"

    # Check for overdue follow-ups
    if "OVERDUE" in followup_text:
        for line in followup_text.split("\n"):
            if "!!!" in line:
                return f"OVERDUE FOLLOW-UP: {line.strip().lstrip('!').strip()[:80]}"

    # Check for expired entries
    if stale.get("expired", 0) > 0:
        return f"ARCHIVE {stale['expired']} expired entry(ies) — deadline passed"

    # Check for at-risk
    if stale.get("at_risk", 0) > 0:
        return f"ADVANCE {stale['at_risk']} at-risk entry(ies) — deadline ≤3 days"

    # Stagnant entries
    if stale.get("stagnant", 0) > 0:
        return f"REVIEW {stale['stagnant']} stagnant entry(ies) — no activity >7 days"

    # Default
    actionable = health.get("actionable", 0)
    if actionable > 0:
        return f"Work pipeline: {actionable} actionable entries"

    return "Pipeline is clean — source new opportunities"


def format_digest(
    health_stats: dict,
    health_text: str,
    stale_stats: dict,
    stale_text: str,
    followup_text: str,
    campaign_text: str,
    funding_text: str,
    top_action: str,
    blind_spot_text: str = "",
    freshness_text: str = "",
) -> str:
    """Format the unified morning digest."""
    today = date.today()
    lines = []

    lines.append("=" * 60)
    lines.append(f"MORNING DIGEST — {today.strftime('%A, %B %d, %Y')}")
    lines.append("=" * 60)
    lines.append("")

    # Top action — the one thing to focus on
    lines.append(f">>> {top_action}")
    lines.append("")

    # Health snapshot (condensed)
    lines.append(f"Pipeline: {health_stats.get('total', 0)} total | "
                 f"{health_stats.get('actionable', 0)} actionable | "
                 f"{health_stats.get('submitted', 0)} submitted")
    days_since = health_stats.get("days_since_last_submission")
    if days_since is not None:
        lines.append(f"Last submission: {days_since} day(s) ago")
    lines.append("")

    # Staleness summary (condensed)
    exp = stale_stats.get("expired", 0)
    risk = stale_stats.get("at_risk", 0)
    stag = stale_stats.get("stagnant", 0)
    if exp + risk + stag > 0:
        alerts = []
        if exp:
            alerts.append(f"{exp} expired")
        if risk:
            alerts.append(f"{risk} at-risk")
        if stag:
            alerts.append(f"{stag} stagnant")
        lines.append(f"Alerts: {' | '.join(alerts)}")
        lines.append("")

    # Follow-up section
    if followup_text.strip():
        lines.append(followup_text.strip())
        lines.append("")

    # Campaign section
    if campaign_text.strip():
        lines.append(campaign_text.strip())
        lines.append("")

    # Funding pulse
    if funding_text.strip():
        lines.append(funding_text.strip())
        lines.append("")

    # Blind spot progress + freshness (new intelligence sections)
    if blind_spot_text:
        lines.append(blind_spot_text)
    if freshness_text:
        lines.append(freshness_text)
    if blind_spot_text or freshness_text:
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def run_morning(brief: bool = False, save: bool = False):
    """Execute the full morning sequence."""
    # Automatic freshness gate — flush stale job entries before reporting
    from pipeline_freshness import flush_stale_active_jobs
    flush_stale_active_jobs()

    # Auto-expire job submissions with no response after 21 days
    # (PIPELINE_NO_MUTATE forces a dry run so tests don't mutate the real tree)
    import os

    from hygiene import run_expire_stale_submissions
    all_for_expire = load_entries()
    run_expire_stale_submissions(
        all_for_expire, max_days=21, dry_run=bool(os.environ.get("PIPELINE_NO_MUTATE"))
    )

    entries = load_entries()  # reload after potential expirations
    if not entries:
        print("No pipeline entries found.")
        sys.exit(1)

    # Gather all sections
    health_stats, health_text = get_health(entries)
    stale_stats, stale_text = get_stale(entries)
    _, followup_text = get_followup(entries)
    campaign_text = get_campaign(entries)
    _, funding_text = get_funding()

    top_action = compute_top_action(health_stats, stale_stats, campaign_text, followup_text)

    if brief:
        print(top_action)
        return

    # Intelligence sections (graceful — never block digest)
    blind_spot_text = get_blind_spot_progress()
    freshness_text = get_freshness_summary(entries)

    digest = format_digest(
        health_stats, health_text,
        stale_stats, stale_text,
        followup_text, campaign_text,
        funding_text, top_action,
        blind_spot_text, freshness_text,
    )

    print(digest)

    if save:
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"morning-digest-{date.today().isoformat()}.md"
        path = SIGNALS_DIR / filename
        path.write_text(digest + "\n")
        print(f"\nSaved to: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Morning autopilot: unified morning digest"
    )
    parser.add_argument("--brief", action="store_true",
                        help="Top action only (one line)")
    parser.add_argument("--save", action="store_true",
                        help="Save digest to signals/morning-digest-{date}.md")
    args = parser.parse_args()

    run_morning(brief=args.brief, save=args.save)


if __name__ == "__main__":
    main()
