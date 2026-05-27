#!/usr/bin/env python3
"""Daily glove-fit ingestion: fetch, pre-score, and surface top-tier job matches.

Wraps the existing fetch pipeline with a pre-scoring filter and identity match,
then surfaces the Top N ranked results. Promotes qualifying entries directly to
pipeline/active/ as 'qualified' (bypassing research_pool/).

Usage:
    python scripts/ingest_top_roles.py                      # Fetch + filter + Top 10 display (dry-run)
    python scripts/ingest_top_roles.py --min-score 9.0      # Override threshold (default: 9.0)
    python scripts/ingest_top_roles.py --top 20             # Show more results (default: 10)
    python scripts/ingest_top_roles.py --all-tiers          # Skip identity filter, show any role >= threshold
    python scripts/ingest_top_roles.py --promote --yes      # Write qualifying entries to pipeline/active/ as qualified
    python scripts/ingest_top_roles.py --promote --dry-run  # Preview what would be promoted
"""

import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    COMPANY_CAP,
    PIPELINE_DIR_ACTIVE,
    check_company_cap,
    get_portal_scores,
    get_strategic_base,
    load_entries,
)
from score import (
    HIGH_PRESTIGE,
    ROLE_FIT_TIERS,
    WEIGHTS_JOB,
)
from source_jobs import (
    TITLE_EXCLUDES,
    TITLE_KEYWORDS,
    _get_existing_ids,
    create_pipeline_entry,
    deduplicate,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    filter_by_title,
    load_sources,
)

DEFAULT_MIN_SCORE = 9.0
DEFAULT_TOP_N = 5

# Identity match: title patterns that indicate strong DevEx/DevRel/agentic fit.
# A role passing this filter is a "glove fit" — not just a good score,
# but directly aligned with the independent-engineer identity position.
IDENTITY_KEYWORDS = [
    "developer experience", "devex", "devtools", "developer tools",
    "developer relations", "devrel", "developer advocate",
    "agentic", "agent sdk", "claude code", "cli",
    "technical writer", "documentation",
]

# Freshness scoring modifiers based on posting age.
# Research shows 48h peak, 14d black hole, 30d+ ghost (shortlist already selected).
FRESHNESS_MODIFIERS: dict[str, float] = {
    "urgent":    1.5,   # 0–2 days: 48-hour peak window
    "fresh":     0.5,   # 3–7 days: still strong
    "standard":  0.0,   # 8–14 days: no modifier
    "aging":    -0.5,   # 15–21 days: declining probability
    "stale":    -1.5,   # 22–30 days: near-black-hole
    "ghost":    -3.0,   # 31+ days: shortlist effectively selected
    "unknown":   0.0,   # No posting date captured
}


def freshness_tier(posting_date: str | None) -> tuple[str, int | None]:
    """Return (tier_name, age_in_days) for a posting date ISO string.

    tier_name is one of: urgent, fresh, standard, aging, stale, ghost, unknown.
    age_in_days is None when posting_date is absent or unparseable.
    """
    if not posting_date:
        return "unknown", None
    try:
        age = (date.today() - date.fromisoformat(posting_date)).days
    except (ValueError, TypeError):
        return "unknown", None
    if age <= 2:
        return "urgent", age
    if age <= 7:
        return "fresh", age
    if age <= 14:
        return "standard", age
    if age <= 21:
        return "aging", age
    if age <= 30:
        return "stale", age
    return "ghost", age


def pre_score(job: dict) -> float:
    """Estimate a composite fit score for a job posting without a full pipeline entry.

    Uses the same dimension weights as score.py (WEIGHTS_JOB) with auto-derived
    values for the non-human dimensions, and title-pattern matching for the
    human judgment dimensions (mission_alignment, evidence_match, track_record_fit).

    Returns an estimated_score float on the 0–10 scale.
    """
    title_lower = job.get("title", "").lower()
    company_display = job.get("company_display", "")
    portal = job.get("portal", "")

    # Human-judgment dimensions: title-tier matching (same logic as estimate_role_fit_from_title)
    human_dims = {"mission_alignment": 5, "evidence_match": 4, "track_record_fit": 4}
    for tier in ROLE_FIT_TIERS:
        for pattern in tier["title_patterns"]:
            if pattern in title_lower:
                human_dims = {
                    "mission_alignment": tier["mission_alignment"],
                    "evidence_match": tier["evidence_match"],
                    "track_record_fit": tier["track_record_fit"],
                }
                break
        else:
            continue
        break

    # Auto-derived dimensions
    strategic_value = HIGH_PRESTIGE.get(company_display, get_strategic_base().get("job", 6))
    financial_alignment = 8   # tech jobs assumed well above benefits cliff
    effort_to_value = 7       # standard
    deadline_feasibility = 9  # rolling deadlines
    portal_friction = get_portal_scores().get(portal, 5)

    dims = {
        "mission_alignment": human_dims["mission_alignment"],
        "evidence_match": human_dims["evidence_match"],
        "track_record_fit": human_dims["track_record_fit"],
        "network_proximity": 1,  # auto-sourced jobs are always cold
        "strategic_value": strategic_value,
        "financial_alignment": financial_alignment,
        "effort_to_value": effort_to_value,
        "deadline_feasibility": deadline_feasibility,
        "portal_friction": portal_friction,
    }

    tier, _ = freshness_tier(job.get("posting_date"))
    freshness_mod = FRESHNESS_MODIFIERS[tier]
    # Pillar dims (studio_alignment, remote_flexibility) aren't estimated here;
    # default them to the neutral 5 that compute_composite also applies.
    score = sum(dims.get(dim, 5) * weight for dim, weight in WEIGHTS_JOB.items())
    return round(max(0.0, min(10.0, score + freshness_mod)), 2)


def identity_match(job: dict) -> bool:
    """Return True if the job title matches the independent-engineer identity keywords."""
    title_lower = job.get("title", "").lower()
    return any(kw in title_lower for kw in IDENTITY_KEYWORDS)


def fetch_all_jobs(sources: dict) -> list[dict]:
    """Fetch and filter jobs from all configured sources."""
    all_jobs: list[dict] = []

    for board in sources.get("greenhouse") or []:
        jobs = fetch_greenhouse_jobs(board)
        all_jobs.extend(jobs)

    for company in sources.get("lever") or []:
        jobs = fetch_lever_jobs(company)
        all_jobs.extend(jobs)

    for company in sources.get("ashby") or []:
        jobs = fetch_ashby_jobs(company)
        all_jobs.extend(jobs)

    return all_jobs


def write_active_entry(entry_id: str, entry: dict) -> Path:
    """Write a pipeline entry to pipeline/active/ with status=qualified."""
    PIPELINE_DIR_ACTIVE.mkdir(parents=True, exist_ok=True)
    filepath = PIPELINE_DIR_ACTIVE / f"{entry_id}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(entry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return filepath


def run(
    min_score: float = DEFAULT_MIN_SCORE,
    top_n: int = DEFAULT_TOP_N,
    all_tiers: bool = False,
    promote: bool = False,
    dry_run: bool = True,
    max_age: int | None = None,
):
    """Main entry point for glove-fit ingestion."""
    today = date.today().isoformat()

    print(f"GLOVE-FIT INGESTION — {today}")
    age_filter_label = f"  |  Max age: {max_age}d" if max_age is not None else ""
    print(f"Threshold: ≥ {min_score}  |  Identity filter: {'off' if all_tiers else 'on'}{age_filter_label}")
    print("=" * 60)
    print()

    # Load sources
    sources = load_sources()

    # Fetch all jobs
    print("Fetching jobs...")
    all_jobs = fetch_all_jobs(sources)
    print(f"  Fetched {len(all_jobs)} total postings")

    # Apply title keyword filter (same as source_jobs.py)
    filtered = filter_by_title(all_jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
    print(f"  {len(filtered)} after title filter")

    # Deduplicate against existing pipeline entries
    existing_ids = _get_existing_ids()
    unique = deduplicate(filtered, existing_ids)
    print(f"  {len(unique)} new (not yet in pipeline)")

    # Apply max-age filter if requested
    if max_age is not None:
        unique = [j for j in unique
                  if freshness_tier(j.get("posting_date"))[1] is not None
                  and freshness_tier(j.get("posting_date"))[1] <= max_age]
        print(f"  {len(unique)} after max-age filter (≤ {max_age} days)")

    print()

    if not unique:
        print("No new matching jobs found.")
        return

    # Pre-score all unique jobs
    scored = []
    for job in unique:
        score = pre_score(job)
        matches_identity = identity_match(job)
        tier, age = freshness_tier(job.get("posting_date"))
        scored.append({**job, "_score": score, "_identity": matches_identity,
                        "_tier": tier, "_age": age})

    # Apply threshold + identity filter
    qualifying = [
        j for j in scored
        if j["_score"] >= min_score and (all_tiers or j["_identity"])
    ]
    qualifying.sort(key=lambda j: -j["_score"])

    if not qualifying:
        print(f"No roles met threshold ≥ {min_score}" + ("" if all_tiers else " with identity match") + ".")

        # Show near-misses
        near_miss = [j for j in scored if j["_score"] >= min_score - 0.5]
        near_miss.sort(key=lambda j: -j["_score"])
        if near_miss:
            print(f"\nNear-misses (score ≥ {min_score - 0.5}, below threshold or no identity match):")
            for j in near_miss[:5]:
                id_tag = "✓" if j["_identity"] else "✗"
                t, a = freshness_tier(j.get("posting_date"))
                age_str = f"Day {a}" if a is not None else "--"
                print(f"  {j['_score']:.1f}  [{id_tag}]  {age_str:<9}  {j['company_display']:<20}  {j['title']}")
        return

    display = qualifying[:top_n]

    # Determine tier name for display
    def get_tier_name(job: dict) -> str:
        title_lower = job.get("title", "").lower()
        for tier in ROLE_FIT_TIERS:
            for pattern in tier["title_patterns"]:
                if pattern in title_lower:
                    return tier["name"]
        return "unmatched"

    print(f"TOP {min(top_n, len(qualifying))} GLOVE FITS  (score ≥ {min_score}" + (", identity match)" if not all_tiers else ")"))
    print("─" * 75)
    print(f"  {'#':>2}  {'Score':>5}  {'Age':<9}  {'Tier':<18}  {'Company':<20}  Role")
    print("─" * 75)

    for idx, job in enumerate(display, 1):
        freshness_t = job.get("_tier", "unknown")
        age = job.get("_age")
        age_str = f"Day {age}" if age is not None else "--"
        # For stale/ghost tiers, show freshness status instead of role tier to flag risk
        if freshness_t in ("ghost", "stale"):
            tier_display = f"[{freshness_t}]"
        else:
            tier_display = get_tier_name(job)
        id_tag = " ✓" if job["_identity"] else ""
        print(f"  {idx:>2}  {job['_score']:.1f}   {age_str:<9}  {tier_display:<18}  {job['company_display']:<20}  {job['title']}{id_tag}")
        print(f"       {job['url']}")

    if len(qualifying) > top_n:
        print(f"\n  ... and {len(qualifying) - top_n} more qualifying roles (use --top {len(qualifying)} to see all)")

    print()

    if not promote:
        print(f"Dry-run: {len(qualifying)} qualifying roles found. Use --promote --yes to write to pipeline/active/")
        return

    # Promote mode
    promoted = []
    skipped = []
    all_entries = load_entries()

    for job in qualifying:
        entry_id, entry = create_pipeline_entry(job)

        # Override: promote directly to active/ as qualified
        entry["status"] = "qualified"
        entry["source"] = "ingest_top_roles.py"
        entry["tags"] = ["auto-sourced", "glove-fit"]
        entry["fit"]["score"] = job["_score"]

        # Check if active/ file would overwrite something
        dest = PIPELINE_DIR_ACTIVE / f"{entry_id}.yaml"
        if dest.exists():
            skipped.append(entry_id)
            continue

        # Enforce company cap
        org_name = (entry.get("target") or {}).get("organization", "")
        allowed, current = check_company_cap(org_name, all_entries)
        if not allowed:
            print(f"  SKIP {entry_id}: {org_name} at cap ({current}/{COMPANY_CAP})")
            skipped.append(entry_id)
            continue

        if dry_run:
            promoted.append((entry_id, entry))
            print(f"  [dry-run] would promote: {entry_id}")
        else:
            filepath = write_active_entry(entry_id, entry)
            promoted.append((entry_id, entry))
            print(f"  [promoted] {entry_id} → {filepath.relative_to(Path.cwd())}")

    print()
    if dry_run:
        print(f"Dry-run complete: {len(promoted)} would be promoted, {len(skipped)} already exist.")
        print("Run with --promote --yes to execute.")
    else:
        print(f"Promoted {len(promoted)} entries to pipeline/active/ (status=qualified)")
        if skipped:
            print(f"Skipped {len(skipped)} (already in active/): {', '.join(skipped)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Glove-fit ingestion: fetch, pre-score, and surface top job matches"
    )
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE, metavar="N",
                        help=f"Minimum pre-score threshold (default: {DEFAULT_MIN_SCORE})")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N, metavar="N",
                        help=f"Number of top results to display (default: {DEFAULT_TOP_N})")
    parser.add_argument("--all-tiers", action="store_true",
                        help="Skip identity filter — show any role meeting the score threshold")
    parser.add_argument("--promote", action="store_true",
                        help="Write qualifying entries to pipeline/active/ as qualified")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview promotions without writing files (default when --yes is absent)")
    parser.add_argument("--yes", action="store_true",
                        help="Execute promotions (required with --promote to write files)")
    parser.add_argument("--max-age", type=int, default=None, metavar="DAYS",
                        help="Exclude postings older than N days (skips postings with unknown date)")
    args = parser.parse_args()

    dry_run = not args.yes or args.dry_run

    run(
        min_score=args.min_score,
        top_n=args.top,
        all_tiers=args.all_tiers,
        promote=args.promote,
        dry_run=dry_run,
        max_age=args.max_age,
    )


if __name__ == "__main__":
    main()
