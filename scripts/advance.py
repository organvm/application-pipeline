#!/usr/bin/env python3
"""Batch-advance pipeline entries through status stages.

Addresses the qualified → drafting logjam by enabling batch progression
with validation, dry-run preview, and an advancement report.

Two-tier enforcement model:
    advance.py is **permissive by design** — it warns and skips entries that
    violate org-cap constraints but does not block the overall operation.
    triage.py is the **enforcement backstop** — it actively demotes excess
    entries to restore compliance. This separation lets the user advance
    entries optimistically while triage ensures invariants hold.

Usage:
    python scripts/advance.py --report
    python scripts/advance.py --dry-run --to drafting --effort quick
    python scripts/advance.py --to drafting --effort quick --yes
    python scripts/advance.py --to staged --id pen-america
"""

import argparse
import datetime
import shutil
import sys
from pathlib import Path

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    COMPANY_CAP,
    REPO_ROOT,
    VALID_TRANSITIONS,
    check_company_cap,
    days_until,
    get_deadline,
    get_effort,
    get_score,
    load_entries,
    load_profile,
    update_last_touched,
    update_yaml_field,
)

# Map target status to timeline field to set
STATUS_TIMELINE_FIELD = {
    "qualified": "qualified",
    "drafting": None,  # no timeline field for drafting
    "staged": "materials_ready",
    "submitted": "submitted",
    "acknowledged": "acknowledged",
    "interview": "interview",
    "outcome": "outcome_date",
}


def can_advance(current_status: str, target_status: str) -> bool:
    """Check if a transition is valid."""
    return target_status in VALID_TRANSITIONS.get(current_status, set())


def has_outreach_actions(entry: dict) -> bool:
    """Check if an entry has at least one outreach or follow-up action recorded."""
    follow_up = entry.get("follow_up") or []
    outreach = entry.get("outreach") or []
    return len(follow_up) > 0 or len(outreach) > 0


def _posting_age_days(entry: dict) -> int | None:
    """Return age in days for an entry's posting_date, if it is parseable."""
    timeline = entry.get("timeline") or {}
    posting_date = entry.get("posting_date")
    if posting_date is None and isinstance(timeline, dict):
        posting_date = timeline.get("posting_date")
    if not posting_date:
        return None

    if isinstance(posting_date, datetime.datetime):
        posting_day = posting_date.date()
    elif isinstance(posting_date, datetime.date):
        posting_day = posting_date
    else:
        try:
            posting_day = datetime.date.fromisoformat(str(posting_date).strip()[:10])
        except ValueError:
            return None

    today = datetime.date.today()
    age = (today - posting_day).days
    return age


def _log_gate_bypass(entry_id: str, gate_name: str) -> None:
    """Log a signal-action audit entry when a gate is bypassed."""
    try:
        from log_signal_action import log_action
        log_action(
            signal_id=f"gate-bypass-{entry_id}-{datetime.date.today().isoformat()}",
            signal_type="gate_bypass",
            description=f"Outreach gate bypassed via --skip-outreach-gate for {entry_id}",
            triggered_action=f"bypassed {gate_name} gate",
            entry_id=entry_id,
            reason="User explicitly skipped gate",
        )
    except Exception:
        pass  # Best-effort audit logging


def advance_entry(filepath, entry_id: str, target_status: str, reason: str | None = None) -> bool:
    """Advance a single entry to target_status by updating the YAML file.

    Returns True if successful. Logs to signal-action audit trail.
    The optional reason is included in the signal-action log entry.
    """
    content = filepath.read_text()
    today_str = datetime.date.today().isoformat()

    # Read current status before modification
    import yaml as _yaml
    current_data = _yaml.safe_load(content) or {}
    from_status = current_data.get("status", "?")

    # Update status
    content = update_yaml_field(content, "status", target_status)

    # Update last_touched
    content = update_last_touched(content)

    # Update timeline field if applicable
    tl_field = STATUS_TIMELINE_FIELD.get(target_status)
    if tl_field:
        try:
            content = update_yaml_field(
                content, tl_field, f"'{today_str}'", nested=True,
            )
        except ValueError:
            pass  # Field may not exist in this entry

    filepath.write_text(content)

    # Log signal-action for audit trail
    try:
        from log_signal_action import log_action
        description = f"Advanced {from_status} -> {target_status}"
        if reason:
            description = f"{description} ({reason})"
        log_action(
            signal_id=f"advance-{entry_id}-{today_str}",
            signal_type="score_threshold",
            description=description,
            triggered_action=f"advance to {target_status}",
            entry_id=entry_id,
            reason=reason,
        )
    except Exception as e:
        print(f"  [audit] Signal logging failed: {e}", file=sys.stderr)

    return True


def run_report(entries: list[dict]):
    """Show advancement opportunities and blockers."""
    print("ADVANCEMENT REPORT")
    print("=" * 70)
    print()

    ready = []
    blocked = []

    for e in entries:
        status = e.get("status", "")
        if status not in ACTIONABLE_STATUSES:
            continue

        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        score = get_score(e)
        effort = get_effort(e)
        dl_date, dl_type = get_deadline(e)

        # Determine next natural status
        next_status = None
        if status == "research":
            next_status = "qualified"
        elif status == "qualified":
            next_status = "drafting"
        elif status == "drafting":
            next_status = "staged"
        elif status == "staged":
            next_status = "submitted"

        if not next_status:
            continue

        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                dl_str = f"EXPIRED {abs(d)}d ago"
            else:
                dl_str = f"{d}d left"
        elif dl_type in ("rolling", "tba"):
            dl_str = dl_type

        has_profile = load_profile(entry_id) is not None

        # Determine readiness
        blockers = []
        if status in ("qualified", "drafting") and not has_profile:
            blockers.append("no profile")
        if dl_date and days_until(dl_date) < 0:
            blockers.append("expired deadline")

        item = {
            "id": entry_id,
            "name": name,
            "status": status,
            "next": next_status,
            "effort": effort,
            "score": score,
            "dl_str": dl_str,
            "has_profile": has_profile,
            "blockers": blockers,
        }

        if blockers:
            blocked.append(item)
        else:
            ready.append(item)

    # Sort ready by score descending
    ready.sort(key=lambda x: -x["score"])

    if ready:
        print(f"READY TO ADVANCE ({len(ready)}):")
        for item in ready:
            profile_str = "yes" if item["has_profile"] else "no"
            print(f"  {item['name']}")
            print(f"    {item['status']} -> {item['next']} | "
                  f"{item['effort']} | score {item['score']:.1f} | "
                  f"{item['dl_str']} | profile: {profile_str}")
        print()

    if blocked:
        print(f"BLOCKED ({len(blocked)}):")
        for item in blocked:
            print(f"  {item['name']}")
            print(f"    {item['status']} | {', '.join(item['blockers'])}")
        print()

    if not ready and not blocked:
        print("No actionable entries to advance.")
        print()

    # Summary
    total_actionable = len(ready) + len(blocked)
    print(f"Summary: {len(ready)} ready, {len(blocked)} blocked, "
          f"{total_actionable} total actionable")


def _backup_files(files: list, label: str = "advance") -> None:
    """Snapshot files to pipeline/.backup/{timestamp}/ before modification."""
    if not files:
        return
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = REPO_ROOT / "pipeline" / ".backup" / f"{ts}-{label}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f and f.exists():
            shutil.copy2(f, backup_dir / f.name)
    print(f"  Backup: {backup_dir.relative_to(REPO_ROOT)} ({len(files)} files)")


def run_advance(
    target_status: str,
    effort_filter: str | None,
    status_filter: str | None,
    entry_id: str | None,
    dry_run: bool,
    auto_yes: bool,
    backup: bool = False,
    force: bool = False,
    strict: bool = False,
):
    """Advance entries matching filters to target_status."""
    entries = load_entries(include_filepath=True)

    candidates = []
    for e in entries:
        current = e.get("status", "")
        eid = e.get("id", "?")

        # Filter by specific ID
        if entry_id and eid != entry_id:
            continue

        # Filter by current status
        if status_filter and current != status_filter:
            continue

        # Must be a valid transition
        if not can_advance(current, target_status):
            continue

        # Filter by effort
        if effort_filter and get_effort(e) != effort_filter:
            continue

        # Must be actionable (or deferred, which can be re-activated)
        if current not in ACTIONABLE_STATUSES and current != "deferred":
            continue

        # Enforce company cap when advancing to staged or submitted
        if target_status in ("staged", "submitted"):
            age = _posting_age_days(e)
            if age is not None and age > 1 and not force:
                print(f"SKIP {eid}: posting is {age} days old (24h freshness gate)")
                continue

            org = (e.get("target") or {}).get("organization", "")
            if org:
                allowed, current_count = check_company_cap(org, entries)
                if not allowed:
                    print(f"  SKIP {eid}: {org} at cap ({current_count}/{COMPANY_CAP})")
                    continue

        # Gate: require outreach before advancing to submitted
        if target_status == "submitted":
            if not has_outreach_actions(e):
                if strict:
                    print(f"  BLOCKED {eid}: No outreach actions recorded "
                          f"(strict mode — gate cannot be bypassed)")
                    continue
                elif force:
                    print(f"  WARNING {eid}: Outreach gate skipped (--skip-outreach-gate)")
                    _log_gate_bypass(eid, "outreach")
                else:
                    print(f"  BLOCKED {eid}: No outreach actions recorded. "
                          f"Use followup.py --log to record outreach first.")
                    continue

        candidates.append(e)

    if not candidates:
        print("No entries match the specified filters for advancement.")
        return

    print(f"{'DRY RUN: ' if dry_run else ''}Advancing {len(candidates)} entries → {target_status}")
    print(f"{'─' * 60}")

    # Stage order for skip detection
    _STATUS_ORDER = ["research", "qualified", "drafting", "staged", "submitted"]

    for e in candidates:
        eid = e.get("id", "?")
        name = e.get("name", eid)
        current = e.get("status", "?")
        filepath = e.get("_filepath")

        # Warn when skipping intermediate stages
        try:
            current_idx = _STATUS_ORDER.index(current)
            target_idx = _STATUS_ORDER.index(target_status)
            if target_idx - current_idx > 1:
                skipped = _STATUS_ORDER[current_idx + 1:target_idx]
                print(f"  [WARN] {name}: skipping stage(s) {skipped} — "
                      f"run compose.py/draft.py before submitting")
        except ValueError:
            pass

        print(f"  {name}: {current} → {target_status}")

    if dry_run:
        print(f"{'─' * 60}")
        print(f"Dry run complete. {len(candidates)} entries would be advanced.")
        return

    # Confirmation
    if not auto_yes:
        print(f"{'─' * 60}")
        try:
            confirm = input("Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if confirm != "y":
            print("Aborted.")
            return

    # Backup before modification
    if backup:
        _backup_files([e.get("_filepath") for e in candidates], label="advance")

    # Determine reason based on context
    if entry_id:
        reason = "Manual advancement by user"
    elif effort_filter:
        reason = f"Batch advance: effort={effort_filter}"
    elif status_filter:
        reason = f"Batch advance: from {status_filter}"
    else:
        reason = None

    # Execute
    advanced = 0
    for e in candidates:
        eid = e.get("id", "?")
        filepath = e.get("_filepath")
        if filepath:
            advance_entry(filepath, eid, target_status, reason=reason)
            advanced += 1

            # Auto-generate outreach LinkedIn search URLs on advancement to staged/drafting
            if target_status in ("staged", "drafting") and e.get("track") == "job":
                _generate_outreach_urls(filepath, e)

    print(f"{'─' * 60}")
    print(f"Advanced {advanced} entries to '{target_status}'.")


def _generate_outreach_urls(filepath: Path, entry: dict) -> None:
    """Auto-generate LinkedIn search URLs for outreach when entry is advanced.

    Writes an 'outreach' field to the entry YAML with search URLs
    based on the org and role title.
    """
    from urllib.parse import quote

    org = (entry.get("target") or {}).get("organization", "")
    title = (entry.get("name") or "").lower()
    if not org:
        return

    # Derive search terms from role context
    if "forward deployed" in title or "fde" in title:
        terms = ["Head of Forward Deployed Engineering", "Engineering Manager"]
    elif "solutions engineer" in title:
        terms = ["Solutions Engineering Manager", "Head of Solutions"]
    elif "technical writer" in title or "documentation" in title:
        terms = ["Technical Writing Manager", "Head of Documentation"]
    elif "developer advocate" in title or "devrel" in title:
        terms = ["Head of Developer Relations", "DevRel Manager"]
    elif "agent" in title:
        terms = ["Engineering Manager AI", "Head of AI"]
    elif "platform" in title or "infrastructure" in title:
        terms = ["Engineering Manager Platform", "VP Engineering"]
    elif "full stack" in title or "full-stack" in title or "staff" in title:
        terms = ["Engineering Manager", "VP Engineering"]
    else:
        terms = ["Engineering Manager", "VP Engineering"]

    linkedin_searches = []
    for term in terms[:2]:
        query = quote(f"{term} {org}")
        url = f"https://www.linkedin.com/search/results/people/?keywords={query}&origin=GLOBAL_SEARCH_HEADER"
        linkedin_searches.append({"role": term, "search_url": url})

    # Write to YAML under outreach_research (NOT outreach): these are planned
    # search aids, not logged outreach actions. Keeping them out of `outreach`
    # preserves the schema (outreach is a list of actions) and the submitted
    # outreach-evidence gate (which must require a real recorded action).
    try:
        import yaml as _yaml
        data = _yaml.safe_load(filepath.read_text())
        data["outreach_research"] = {
            "linkedin_searches": linkedin_searches,
            "contact_name": None,
            "contact_url": None,
            "status": "pending",
        }
        filepath.write_text(_yaml.dump(data, default_flow_style=False, sort_keys=False))
        print(f"  → Outreach research URLs generated for {org}")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Batch-advance pipeline entries through status stages"
    )
    parser.add_argument("--to", dest="target_status",
                        help="Target status to advance entries to")
    parser.add_argument("--effort", choices=["quick", "standard", "deep", "complex"],
                        help="Filter by effort level")
    parser.add_argument("--status",
                        help="Filter by current status (default: infer from --to)")
    parser.add_argument("--id", dest="entry_id",
                        help="Advance a specific entry by ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying files")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--report", action="store_true",
                        help="Show advancement opportunities and blockers")
    parser.add_argument("--backup", action="store_true",
                        help="Snapshot modified files to pipeline/.backup/ before writing")
    parser.add_argument("--skip-outreach-gate", action="store_true",
                        help="Bypass outreach gate when advancing to submitted")
    parser.add_argument("--force", action="store_true", dest="skip_outreach_gate",
                        help="(deprecated alias for --skip-outreach-gate)")
    parser.add_argument("--strict", action="store_true",
                        help="Strict mode: disables --skip-outreach-gate and enforces all gates")
    args = parser.parse_args()

    if args.report:
        entries = load_entries()
        run_report(entries)
        return

    if not args.target_status:
        parser.error("Specify --to <status> or --report")

    if args.strict and args.skip_outreach_gate:
        parser.error("--strict and --skip-outreach-gate are mutually exclusive")

    run_advance(
        target_status=args.target_status,
        effort_filter=args.effort,
        status_filter=args.status,
        entry_id=args.entry_id,
        dry_run=args.dry_run,
        auto_yes=args.yes,
        backup=args.backup,
        force=args.skip_outreach_gate,
        strict=args.strict,
    )


if __name__ == "__main__":
    main()
