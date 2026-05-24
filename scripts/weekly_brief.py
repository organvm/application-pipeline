#!/usr/bin/env python3
"""Weekly executive brief generator.

Produces a compact weekly brief with:
1) pipeline snapshot and submission velocity
2) readiness blockers from submission audit rules
3) warm intro queue priorities
4) failure-theme and rejection taxonomy trends
5) hypothesis prediction accuracy

Usage:
    python scripts/weekly_brief.py
    python scripts/weekly_brief.py --save
    python scripts/weekly_brief.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_outcomes import extract_failure_themes
from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_SUBMITTED,
    REPO_ROOT,
    SIGNALS_DIR,
    load_entries,
    parse_date,
)
from submission_audit import PRE_SUBMIT_STATUSES, check_entry
from velocity_report import calculate_hypothesis_accuracy, load_conversion_log, load_hypotheses
from warm_intro_audit import generate_audit_report


def _in_window(raw_date: str | None, *, start_date: date) -> bool:
    parsed = parse_date(raw_date)
    return parsed is not None and parsed >= start_date


def _entry_portal(entry: dict) -> str:
    target = entry.get("target", {})
    if isinstance(target, dict):
        return str(target.get("portal") or "unknown")
    return "unknown"


def compute_snapshot(
    active_entries: list[dict],
    submitted_entries: list[dict],
    closed_entries: list[dict],
    *,
    week_days: int,
) -> dict:
    """Compute status snapshot and weekly submission velocity."""
    all_entries = active_entries + submitted_entries + closed_entries
    statuses = Counter(str(entry.get("status") or "unknown") for entry in all_entries)
    week_start = date.today() - timedelta(days=max(1, week_days) - 1)

    weekly_submissions = 0
    weekly_by_portal: Counter[str] = Counter()
    for entry in all_entries:
        timeline = entry.get("timeline", {})
        submitted_raw = timeline.get("submitted") if isinstance(timeline, dict) else None
        if not _in_window(submitted_raw, start_date=week_start):
            continue
        weekly_submissions += 1
        weekly_by_portal[_entry_portal(entry)] += 1

    actionable = sum(
        statuses.get(state, 0)
        for state in ("research", "qualified", "drafting", "staged", "deferred")
    )
    submitted_awaiting = sum(
        statuses.get(state, 0)
        for state in ("submitted", "acknowledged", "interview")
    )

    return {
        "total_entries": len(all_entries),
        "active_entries": len(active_entries),
        "submitted_entries": len(submitted_entries),
        "closed_entries": len(closed_entries),
        "actionable": actionable,
        "submitted_awaiting": submitted_awaiting,
        "statuses": dict(sorted(statuses.items())),
        "weekly_submissions": weekly_submissions,
        "weekly_submissions_by_portal": dict(weekly_by_portal.most_common()),
    }


def compute_readiness_summary(active_entries: list[dict]) -> dict:
    """Summarize submission readiness blockers across pre-submit entries."""
    candidates = [entry for entry in active_entries if entry.get("status") in PRE_SUBMIT_STATUSES]
    audits = [check_entry(entry, deep=False, config=None) for entry in candidates]

    ready_count = sum(1 for result in audits if result.get("ready"))
    blocker_counter: Counter[str] = Counter()
    staged_sla_breaches = 0
    staged_review_pending = 0

    for result in audits:
        for check_name, ok in (result.get("results") or {}).items():
            if not ok:
                blocker_counter[check_name] += 1

        if result.get("status") == "staged":
            checks = result.get("results", {})
            if checks.get("staged_sla") is False:
                staged_sla_breaches += 1
            if checks.get("review_approved") is False:
                staged_review_pending += 1

    return {
        "total_audited": len(audits),
        "ready": ready_count,
        "blocked": len(audits) - ready_count,
        "staged_sla_breaches": staged_sla_breaches,
        "staged_review_pending": staged_review_pending,
        "top_blockers": [
            {"check": check_name, "count": count}
            for check_name, count in blocker_counter.most_common(6)
        ],
    }


def compute_conversion_summary(*, week_days: int) -> dict:
    """Summarize conversion-log and hypothesis signal for the weekly brief."""
    week_start = date.today() - timedelta(days=max(1, week_days) - 1)
    log_entries = load_conversion_log()

    weekly_submissions = []
    weekly_responses = []
    portal_counter: Counter[str] = Counter()
    for item in log_entries:
        submitted_raw = item.get("submission_date") or item.get("submitted")
        if _in_window(submitted_raw, start_date=week_start):
            weekly_submissions.append(item)
            target = item.get("target")
            if isinstance(target, dict):
                portal = str(target.get("portal") or "unknown")
            else:
                portal = str(item.get("portal") or "unknown")
            portal_counter[portal] += 1

        response_raw = item.get("response_date")
        outcome = item.get("outcome")
        if outcome and outcome != "pending" and _in_window(response_raw, start_date=week_start):
            weekly_responses.append(item)

    accepted = sum(1 for item in weekly_responses if item.get("outcome") == "accepted")
    response_rate = (len(weekly_responses) / len(weekly_submissions)) if weekly_submissions else 0.0
    acceptance_rate = (accepted / len(weekly_responses)) if weekly_responses else 0.0

    hypothesis_metrics = calculate_hypothesis_accuracy(load_hypotheses())
    return {
        "weekly_log_submissions": len(weekly_submissions),
        "weekly_responses": len(weekly_responses),
        "weekly_acceptances": accepted,
        "weekly_response_rate": round(response_rate, 3),
        "weekly_acceptance_rate": round(acceptance_rate, 3),
        "weekly_portals": dict(portal_counter.most_common()),
        "hypothesis_accuracy": hypothesis_metrics,
    }


def compute_outreach_summary(all_entries: list[dict]) -> dict:
    """Summarize warm-intro opportunities and top outreach queue."""
    report = generate_audit_report(all_entries)
    summary = report.get("summary", {})
    queue = report.get("outreach_queue") or []
    return {
        "warm_path_pct": int(summary.get("warm_path_pct", 0)),
        "dense_organizations": int(summary.get("dense_organizations", 0)),
        "referral_candidates": int(summary.get("referral_candidates", 0)),
        "outreach_queue_count": int(summary.get("outreach_queue", len(queue))),
        "outreach_queue": queue[:5],
    }


def compute_failure_summary(submitted_entries: list[dict], closed_entries: list[dict], *, months: int) -> dict:
    """Summarize failure reasons/themes from outcome history."""
    themes = extract_failure_themes(submitted_entries + closed_entries, months=max(1, months))
    return {
        "months": int(themes.get("months", months)),
        "total_failures": int(themes.get("total_failures", 0)),
        "top_reasons": [
            {"reason": reason, "count": count}
            for reason, count in list((themes.get("by_reason") or {}).items())[:5]
        ],
        "top_themes": [
            {"theme": theme, "count": count}
            for theme, count in list((themes.get("by_theme") or {}).items())[:5]
        ],
        "by_track": themes.get("by_track", {}),
    }


def build_recommendations(payload: dict) -> list[str]:
    """Generate prioritized executive recommendations."""
    recommendations: list[str] = []
    readiness = payload["readiness"]
    outreach = payload["outreach"]
    failure = payload["failures"]
    conversion = payload["conversion"]
    snapshot = payload["snapshot"]

    if readiness["staged_sla_breaches"] > 0:
        recommendations.append(
            f"Clear {readiness['staged_sla_breaches']} staged SLA breach(es) before net-new research work."
        )
    if readiness["blocked"] > 0 and readiness["top_blockers"]:
        top = readiness["top_blockers"][0]
        recommendations.append(
            f"Primary execution blocker is `{top['check']}` across {top['count']} entries; run targeted unblock sweep."
        )
    if outreach["outreach_queue_count"] > 0 and outreach["outreach_queue"]:
        lead = outreach["outreach_queue"][0]
        recommendations.append(
            f"Prioritize warm intro outreach at {lead['organization']} (entry {lead['entry_id']}) this week."
        )
    if failure["total_failures"] > 0 and failure["top_reasons"]:
        reason = failure["top_reasons"][0]
        recommendations.append(
            f"Top failure reason is `{reason['reason']}` ({reason['count']} cases); update screening criteria."
        )
    if snapshot["weekly_submissions"] == 0:
        recommendations.append("Submission velocity is zero this week; convert at least one ready entry immediately.")
    if conversion["weekly_response_rate"] < 0.2 and conversion["weekly_log_submissions"] > 0:
        recommendations.append(
            "Weekly response rate is low; pivot channel mix toward higher-yield portals and warm-intro lanes."
        )

    if not recommendations:
        recommendations.append("Current execution health is stable; keep weekly cadence and monitor trend drift.")
    return recommendations


def build_brief_payload(*, week_days: int, failure_months: int) -> dict:
    """Build complete weekly brief payload."""
    active_entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    submitted_entries = load_entries(dirs=[PIPELINE_DIR_SUBMITTED])
    closed_entries = load_entries(dirs=[PIPELINE_DIR_CLOSED])
    all_entries = active_entries + submitted_entries + closed_entries

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "week_days": week_days,
        "failure_months": failure_months,
        "snapshot": compute_snapshot(
            active_entries,
            submitted_entries,
            closed_entries,
            week_days=week_days,
        ),
        "readiness": compute_readiness_summary(active_entries),
        "conversion": compute_conversion_summary(week_days=week_days),
        "outreach": compute_outreach_summary(all_entries),
        "failures": compute_failure_summary(submitted_entries, closed_entries, months=failure_months),
    }
    payload["recommendations"] = build_recommendations(payload)
    return payload


def format_markdown(payload: dict) -> str:
    """Render brief payload as markdown."""
    snapshot = payload["snapshot"]
    readiness = payload["readiness"]
    conversion = payload["conversion"]
    outreach = payload["outreach"]
    failures = payload["failures"]
    hypothesis = conversion["hypothesis_accuracy"]

    lines: list[str] = []
    lines.append("# Weekly Executive Brief")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at']}")
    lines.append(
        f"Window: last {payload['week_days']} day(s) | Failure analysis: last {payload['failure_months']} month(s)"
    )
    lines.append("")

    lines.append("## Pipeline Snapshot")
    lines.append(f"- Total entries: {snapshot['total_entries']}")
    lines.append(f"- Active / Submitted / Closed: {snapshot['active_entries']} / {snapshot['submitted_entries']} / {snapshot['closed_entries']}")
    lines.append(f"- Actionable: {snapshot['actionable']}")
    lines.append(f"- Submitted awaiting response: {snapshot['submitted_awaiting']}")
    lines.append(f"- Weekly submissions: {snapshot['weekly_submissions']}")
    if snapshot["weekly_submissions_by_portal"]:
        portals = ", ".join(f"{portal}={count}" for portal, count in snapshot["weekly_submissions_by_portal"].items())
        lines.append(f"- Weekly submissions by portal: {portals}")
    lines.append("")

    lines.append("## Readiness & Blockers")
    lines.append(f"- Audited pre-submit entries: {readiness['total_audited']}")
    lines.append(f"- Ready / Blocked: {readiness['ready']} / {readiness['blocked']}")
    lines.append(f"- Staged SLA breaches: {readiness['staged_sla_breaches']}")
    lines.append(f"- Staged missing review approval: {readiness['staged_review_pending']}")
    if readiness["top_blockers"]:
        lines.append("- Top blockers:")
        for item in readiness["top_blockers"]:
            lines.append(f"  - {item['check']}: {item['count']}")
    lines.append("")

    lines.append("## Conversion & Learning")
    lines.append(f"- Weekly conversion-log submissions: {conversion['weekly_log_submissions']}")
    lines.append(f"- Weekly responses: {conversion['weekly_responses']}")
    lines.append(f"- Weekly acceptances: {conversion['weekly_acceptances']}")
    lines.append(f"- Weekly response rate: {conversion['weekly_response_rate'] * 100:.1f}%")
    lines.append(f"- Weekly acceptance rate: {conversion['weekly_acceptance_rate'] * 100:.1f}%")
    lines.append(f"- Hypothesis accuracy: {hypothesis['accuracy'] * 100:.1f}% ({hypothesis['correct']}/{hypothesis['total']})")
    if conversion["weekly_portals"]:
        portals = ", ".join(f"{portal}={count}" for portal, count in conversion["weekly_portals"].items())
        lines.append(f"- Weekly portal mix: {portals}")
    lines.append("")

    lines.append("## Warm Intro Priorities")
    lines.append(f"- Warm-path coverage: {outreach['warm_path_pct']}%")
    lines.append(f"- Dense organizations: {outreach['dense_organizations']}")
    lines.append(f"- Referral candidates: {outreach['referral_candidates']}")
    lines.append(f"- Outreach queue size: {outreach['outreach_queue_count']}")
    if outreach["outreach_queue"]:
        lines.append("- Top queue:")
        for item in outreach["outreach_queue"]:
            lines.append(
                f"  - {item['organization']} ({item['entry_id']}) owner={item['assignee']} "
                f"due={item['due_date']} — {item['next_action']}"
            )
    lines.append("")

    lines.append("## Failure Themes")
    lines.append(f"- Failures analyzed: {failures['total_failures']}")
    if failures["top_reasons"]:
        reasons = ", ".join(f"{x['reason']}={x['count']}" for x in failures["top_reasons"])
        lines.append(f"- Top reasons: {reasons}")
    if failures["top_themes"]:
        themes = ", ".join(f"{x['theme']}={x['count']}" for x in failures["top_themes"])
        lines.append(f"- Top themes: {themes}")
    if failures["by_track"]:
        tracks = ", ".join(f"{track}={count}" for track, count in failures["by_track"].items())
        lines.append(f"- Failure by track: {tracks}")
    lines.append("")

    lines.append("## Executive Actions")
    for idx, recommendation in enumerate(payload["recommendations"], start=1):
        lines.append(f"{idx}. {recommendation}")

    return "\n".join(lines)


def save_brief(markdown: str) -> tuple[Path, Path]:
    """Persist weekly brief to signals/weekly-brief with latest pointer."""
    output_dir = SIGNALS_DIR / "weekly-brief"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dated_path = output_dir / f"weekly-brief-{timestamp}.md"
    latest_path = output_dir / "latest.md"
    dated_path.write_text(markdown)
    latest_path.write_text(markdown)
    return dated_path, latest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly executive brief")
    parser.add_argument("--week-days", type=int, default=7, help="Window for weekly KPIs (default: 7)")
    parser.add_argument("--failure-months", type=int, default=1, help="Window for failure themes (default: 1)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable payload")
    parser.add_argument("--save", action="store_true", help="Save markdown report to signals/weekly-brief")
    parser.add_argument("--notify", action="store_true", help="Dispatch weekly_brief notification after save")
    args = parser.parse_args()

    payload = build_brief_payload(week_days=max(1, args.week_days), failure_months=max(1, args.failure_months))
    markdown = format_markdown(payload)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(markdown)

    if args.save:
        dated_path, latest_path = save_brief(markdown)
        print()
        print(f"Saved brief: {dated_path.relative_to(REPO_ROOT)}")
        print(f"Updated latest: {latest_path.relative_to(REPO_ROOT)}")
        if args.notify:
            try:
                from notify import dispatch_event
                results = dispatch_event("weekly_brief", {
                    "summary": f"Weekly brief saved to {dated_path.name}",
                    "snapshot": payload.get("snapshot", {}),
                })
                for r in results:
                    status = "OK" if r["success"] else "FAILED"
                    print(f"  Notification [{r['channel']}]: {status} — {r['message']}")
            except ImportError:
                print("  Notification dispatch unavailable (notify.py not found)")


if __name__ == "__main__":
    main()
