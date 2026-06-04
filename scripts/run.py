#!/usr/bin/env python3
"""Single-word command dispatcher for the application pipeline.

Maps natural-language command words to script invocations. Designed for
cross-LLM compatibility: any AI that reads this file knows every available
command and can execute the corresponding script.

Usage:
    python scripts/run.py standup
    python scripts/run.py score creative-capital-2027
    python scripts/run.py campaign
    python scripts/run.py --help
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# --- No-argument commands ---
# Consolidated from 88 → 58 commands. Removed aliases that duplicate flags
# available on the underlying script (e.g., "gaps" = textmatch --all --gaps).
COMMANDS = {
    # -- Daily Operations --
    "standup":     ("standup.py", [],                    "Daily dashboard: stale entries, deadlines, priorities, follow-ups"),
    "campaign":    ("campaign.py", [],                   "Deadline-aware campaign view with urgency tiers"),
    "followup":    ("followup.py", [],                   "Today's follow-up actions and overdue items"),
    "outcomes":    ("check_outcomes.py", [],             "Entries awaiting response + stale submissions"),
    "morning":     ("morning.py", [],                    "Morning digest: health + stale + followups + campaign + funding"),
    "deferred":    ("check_deferred.py", [],              "Deferred entries: overdue and upcoming re-activations"),
    "traffic":     ("traffic_signals.py", [],              "Traffic signals: GitHub views, clones, referrers → follow-up triggers"),

    # -- Pipeline Operations --
    "prepare":     ("prepare_submission.py", [],          "Prepare ALL submission materials (resume, cover letter, portal answers, outreach)"),
    "scoreall":    ("score.py", ["--all", "--dry-run"],  "Preview all scores"),
    "qualify":     ("score.py", ["--auto-qualify"],       "Preview auto-qualification"),
    "enrichall":   ("enrich.py", ["--all", "--dry-run"], "Preview all enrichments"),
    "preflight":   ("preflight.py", [],                  "Batch submission readiness"),
    "resumes":     ("build_resumes.py", [],              "Rebuild PDF resumes from JSON/Markdown sources"),
    "coverletters": ("build_cover_letters.py", [],       "Build cover letter PDFs from markdown"),
    "drift":       ("resume_drift_report.py", [],        "Resume drift analysis: batch vs base similarity"),
    "archive":     ("archive_research.py", ["--report"], "Show archival candidates"),
    "prune":       ("research_analytics.py", [],              "Research pool analytics: classify, org-capped, auto-stale, age-stale entries (dry-run)"),
    "triagegate":  ("triage.py", [],                      "Triage gate: demote sub-threshold staged, resolve org-cap"),
    "triage":      ("smart_triage.py", [],               "Smart triage: decay-scored research entry ranking"),

    # -- Analytics --
    "funnel":      ("funnel_report.py", [],              "Conversion funnel analytics"),
    "conversion":  ("conversion_report.py", [],          "Conversion rate report by track/position/score"),
    "dashboard":   ("conversion_dashboard.py", [],       "Rich terminal conversion dashboard"),
    "velocity":    ("velocity.py", [],                   "Pipeline throughput: staleness, deadlines, throughput"),
    "velocity-log": ("velocity_report.py", [],            "Monthly submission velocity and historical conversion"),
    "quarterly":   ("quarterly_report.py", [],             "Quarterly State of Applications analytics report"),
    "rejections":  ("rejection_learner.py", [],              "Rejection learning: correlate factors with outcomes"),
    "risks":       ("outcome_risk.py", [],                   "Predict submission risk and bottleneck likelihood"),
    "blockoutcomes": ("block_outcomes.py", [],                "Block-outcome correlation: golden/toxic blocks"),
    "blockroi":    ("block_roi_analysis.py", [],          "Block acceptance rate ROI analysis"),
    "portfolio":   ("portfolio_analysis.py", [],          "Portfolio analysis: blocks, positions, channels, variants"),
    "snapshot":    ("snapshot.py", ["--report"],              "Pipeline snapshot: counts, scores, trends"),
    "textmatch":   ("text_match.py", ["--all"],             "TF-IDF text match analysis for all entries"),
    "orgs":        ("org_intelligence.py", ["--all"],         "Org intelligence: aggregated org rankings"),
    "skillsgap":   ("skills_gap.py", ["--all"],               "Skills gap analysis across entries"),

    # -- Relationships --
    "crm":         ("crm.py", [],                            "Relationship CRM: contacts, interactions, coverage gaps"),
    "network":     ("network_graph.py", [],                   "Network graph: nodes, edges, tie strength"),
    "netmap":      ("network_graph.py", ["--map"],            "Network map: full tree from you"),
    "netorgs":     ("network_graph.py", ["--orgs"],           "Org reachability: scores, hops, paths per org"),
    "hydrate":     ("hydrate_followups.py", [],              "Hydrate relationship metadata from LinkedIn/Email"),
    "cultivate":   ("cultivate.py", ["--candidates"],       "Relationship cultivation candidates"),
    "warmintro":   ("warm_intro_audit.py", [],            "Warm intro audit: referral paths and org density"),
    "compose-dm":  ("dm_composer.py", ["--all-pending"],  "Compose Protocol-validated acceptance DMs for pending contacts"),
    "log-dm":      ("log_dm.py", [],                       "Log a DM to all 3 signal files (contacts, outreach-log, network)"),

    # -- Validation & Health --
    "recruiter":   ("recruiter_filter.py", [],             "Recruiter/hiring-manager filter: stale metrics, red flags, formatting"),
    "validate":    ("validate.py", [],                   "Pipeline YAML schema validation"),
    "metrics":     ("check_metrics.py", [],              "Metric consistency check across blocks/profiles/strategy"),
    "health":      ("daily_pipeline_health.py", [],      "Daily pipeline integrity and freshness check"),
    "hygiene":     ("hygiene.py", [],                    "Entry data quality report: URLs, staleness, gates"),
    "signals":     ("validate_signals.py", [],              "Validate signal YAML schema integrity"),
    "verifyall":   ("verify_all.py", [],                     "Run full verification gates (matrix + lint + validate + tests)"),
    "monitor":     ("monitor_pipeline.py", [],            "Monitor backup + conversion-log freshness"),
    "scheduler":   ("scheduler_health.py", [],           "Launchd scheduler and agent health check"),
    "freshness":   ("freshness_monitor.py", [],          "Entry freshness report (posting age analysis)"),
    "staleresumes": ("upgrade_resumes.py", [],             "Check for stale resume batch references"),

    # -- Learning --
    "learner":     ("outcome_learner.py", [],            "Outcome learning engine: calibration report"),
    "hypotheses":  ("feedback_capture.py", ["--list"],   "List all recorded outcome hypotheses"),
    "hypotheses-v": ("validate_hypotheses.py", [],        "Validate outcome hypotheses vs actuals"),
    "recalibrate": ("recalibrate.py", [],                "Quarterly rubric recalibration proposal"),
    "retrospective": ("retrospective.py", [],             "Monthly retrospective prompt"),
    "okr":           ("okr.py", [],                       "Quarterly OKR progress"),

    # -- Strategy --
    "market":      ("market_intel.py", [],               "Market conditions, benchmarks, and grant calendar"),
    "funding":     ("funding_scorer.py", ["--pathway"],         "Non-dilutive funding opportunities by viability"),
    "funding-metrics": ("funding_metrics.py", [],            "Aggregate funding performance and velocity metrics"),
    "tracker":     ("blind_spot_tracker.py", [],         "Blind spot progress tracker with actionable items"),

    # -- LinkedIn Content --
    "linkedin":       ("linkedin_composer.py", ["--history"],    "LinkedIn content pipeline: history + series state"),
    "linkedinaudit":  ("linkedin_composer.py", ["--audit-all"],  "Audit all DRAFT/READY LinkedIn posts against Testament"),
    "linkedinnext":   ("linkedin_composer.py", ["--next"],       "Recommend next LinkedIn post based on series analysis"),
    "linkedinblocks": ("linkedin_composer.py", ["--list"],       "List blocks available for LinkedIn adaptation"),

    # -- Content & Jobs --
    "sourcejobs":  ("source_jobs.py", ["--fetch", "--dry-run"], "Preview new job postings from ATS APIs"),
    "purgejobs":   ("hygiene.py", ["--prune-research", "--flash"], "Archive research_pool entries >72h old (flash reaper)"),
    "keywords":    ("distill_keywords.py", [],           "Extract keywords from job postings"),
    "blocks":      ("generate_project_blocks.py", [],    "Generate blocks from project data"),
    "derive":      ("derive_profile.py", [],             "Derive target profiles from raw evidence blocks"),
    "profiles":    ("generate_job_profile.py", [],       "Generate standardized target profiles from postings"),
    "topjobs":     ("ingest_top_roles.py", [],            "Daily glove-fit fetch: top roles ≥ 9.0 score"),
    "discover":    ("discover_jobs.py", [],                "Skill-based job discovery across free APIs"),
    "scan":        ("scan_orchestrator.py", [],            "Unified scan: all 8 APIs, dedup, pre-score"),
    "match":       ("match_engine.py", [],                 "Auto-score unscored entries, rank top matches"),
    "build":       ("material_builder.py", [],             "LLM-powered material generation (dry-run)"),
    "fullcycle":   ("daily_pipeline_orchestrator.py", [],  "Daily cycle: Scan → Match → Build → Apply → Outreach (dry-run)"),
    "apply":       ("apply_engine.py", [],                    "Readiness check + ATS submission (dry-run)"),
    "outreach":    ("outreach_engine.py", [],                 "Generate outreach templates + set follow-up dates"),
    "calendar":    ("calendar_export.py", [],                 "Export pipeline deadlines to iCal"),
    "interviewprep": ("interview_prep.py", ["--auto"],        "Interview prep for all interview-status entries"),

    # -- Diagnostics --
    "diagnose":    ("diagnose.py", [],                       "System diagnostic scorecard (objective dimensions)"),
    "ira":         ("diagnose_ira.py", [],                   "Inter-rater agreement report (auto-loads ratings/*.json)"),
    "rateall":     ("generate_ratings.py", ["--compute-ira"], "Multi-model rating session with IRA computation"),
    "sysaudit":    ("audit_system.py", [],                   "System integrity audit: claims, wiring, logic"),
    "canonical":   ("verify_canonical.py", [],               "Verify CANONICAL metrics in recruiter_filter.py against actual system state"),
    "intake":      ("score.py", ["--all", "--include-pool"],  "Intake triage: score all entries including research_pool"),
    "validate-external": ("external_validator.py", [],           "Refresh external validation cache and compare"),
    "calibrate":  ("external_validator.py", ["--calibrate"],       "Calibrate thresholds from external data (dry-run)"),
    "mode":        ("pipeline_mode.py", ["--compare"],          "Show pipeline mode and compare thresholds"),
    "standards":   ("standards.py", [],                       "Standards Board: 5-level hierarchical validation audit"),
    "ingest":      ("ingest_historical.py", ["--stats"],        "Historical data ingestion statistics"),
    "phases":      ("phase_analytics.py", [],                    "Phase 1 vs Phase 2 application analytics"),
    "resolve-hyp": ("resolve_hypotheses.py", [],                 "Auto-resolve cold-app hypotheses (dry-run)"),
    "autopreflight": ("daily_pipeline_orchestrator.py", ["--preflight"], "Check autonomous pipeline readiness"),

    # -- Infrastructure --
    "agent":       ("agent.py", ["--plan"],              "Agent: preview planned autonomous actions"),
    "serve":       ("web_api.py", [],                    "Conductor: REST API + dashboard (http://127.0.0.1:8000, docs at /docs)"),
    "acp":         ("acp_server.py", [],                 "Conductor: ACP agent server (http://127.0.0.1:8001, manifest at /agents)"),
    "unblock":     ("unblock_submissions.py", [],        "Identify and resolve submission bottlenecks"),
    "audit":       ("submission_audit.py", [],           "Deep audit of submission materials and history"),
    "automation":  ("launchd_manager.py", ["--status"],  "Launchd automation status"),
    "automation-on": ("launchd_manager.py", ["--install", "--kickstart"], "Install and activate launchd agents"),
    "automation-off": ("launchd_manager.py", ["--uninstall"], "Unload and remove launchd agents"),
    "backup":      ("backup_pipeline.py", ["list"],       "List pipeline backups"),
    "email":       ("check_email.py", [],                 "Check email for submission confirmations"),
    "notify":      ("notify.py", ["--config"],                "Notification dispatcher config check"),
    "weeklybrief": ("weekly_brief.py", [],                   "Weekly executive brief"),
    "status":      ("pipeline_status.py", [],            "Full pipeline status overview"),
    "signallog":   ("log_signal_action.py", ["--list"],   "Signal-to-action audit trail"),
    "quicklog":    ("quicklog.py", [],                   "Quick-log an external submission"),
}

# --- Parameterized commands (word + target ID) ---
PARAM_COMMANDS = {
    "score":    ("score.py", ["--target"],               "Score a single entry"),
    "enrich":   ("enrich.py", ["--id", None, "--all"], "Wire materials/blocks/variants"),
    "advance":  ("advance.py", ["--id"],                 "Advance entry to next status"),
    "compose":  ("compose.py", ["--target"],             "Compose submission from blocks"),
    "draft":    ("draft.py", ["--target"],               "Draft from profile content"),
    "submit":   ("submit.py", ["--target"],              "Generate portal-ready checklist"),
    "apply":    ("apply.py", ["--target"],               "Full application pipeline: fetch questions, generate answers, build PDFs"),
    "check":    ("submit.py", ["--check"],               "Pre-submit validation"),
    "record":   ("submit.py", ["--target", None, "--record"], "Record completed submission"),
    "gate":     ("hygiene.py", ["--gate"],               "Track-specific readiness gate"),
    "contacts":   ("research_contacts.py", ["--target"],  "Research hiring contacts"),
    "hypothesis": ("feedback_capture.py", ["--entry"],   "Capture outcome hypothesis for an entry"),
    "alchemize":  ("alchemize.py", ["--target"],         "End-to-end Greenhouse orchestrator"),
    "answers":    ("answer_questions.py", ["--target"],  "Generate AI-assisted answers for portal questions"),
    "tailor":     ("tailor_resume.py", ["--target"],     "Tailor resume for a specific entry"),
    "review":     ("review_entry.py", ["--target"],        "Mark entry reviewed for governance"),
    "cultivate":  ("cultivate.py", ["--plan"],              "Generate cultivation plan for an entry"),
    "textmatch":  ("text_match.py", ["--target"],            "TF-IDF text match for single entry"),
    "skillsgap":  ("skills_gap.py", ["--target"],            "Skills gap analysis for single entry"),
    "orgdetail":  ("org_intelligence.py", ["--org"],         "Org intelligence detail for single org"),
    "netpath":    ("network_graph.py", ["--path"],             "Find paths to org in network graph"),
    "netscore":   ("network_graph.py", ["--score"],            "Network proximity score for single entry"),
    "interviewprep": ("interview_prep.py", ["--target"],     "Generate interview prep for single entry"),
    "dm":         ("dm_composer.py", ["--contact"],         "Compose acceptance DM for a contact"),
    "logdm":      ("log_dm.py", ["--contact"],             "Log a DM for a contact to all 3 signal files"),
    "greenhouse-submit": ("greenhouse_submit.py", ["--target"], "Greenhouse dry-run preview for single entry"),
    "outreach":   ("outreach_templates.py", ["--target"],       "Generate outreach templates for an entry"),
}


def show_help():
    """Print all available commands."""
    print("Application Pipeline — Single-Word Commands")
    print("=" * 55)
    print()
    print("STANDALONE COMMANDS:")
    for cmd, (script, _, desc) in sorted(COMMANDS.items()):
        print(f"  {cmd:<14s} {desc}")
    print()
    print("PARAMETERIZED COMMANDS (word + entry ID):")
    for cmd, (script, _, desc) in sorted(PARAM_COMMANDS.items()):
        print(f"  {cmd:<14s} {desc}")
    print()
    print("SESSION SEQUENCES:")
    print("  Morning:  morning (or: standup → followup → outcomes → campaign)")
    print("  Submit:   campaign → check <id> → submit <id> → record <id>")
    print("  Research: hygiene → scoreall → qualify → enrichall")
    print("  Analyze:  funnel → conversion → quarterly → blockroi → rejections")
    print("  Strategy: funding → tracker → market")
    print("  Agent:    agent → deferred → signals → hypotheses-v")
    print("  Health:   monitor → freshness → resumes → backup → verifyall")
    print("  Interview: interviewprep <id> → skillsgap <id> → orgdetail <org>")
    print("  Daily Cycle: fullcycle (or: scan → match → build)")
    print()
    print("REMOVED ALIASES (use underlying script flags instead):")
    print("  gaps → textmatch --all --gaps")
    print("  drift → learner (outcome_learner.py --drift-check)")
    print("  enrichnetwork → enrich.py --network")
    print("  reachable → score.py --reachable")
    print("  triagestaged → score.py --triage-staged")
    print()
    print("Usage: python scripts/run.py <command> [args...]")


def run_command(
    cmd: str,
    target: str | None = None,
    extra_args: list[str] | None = None,
):
    """Execute a command."""
    extra_args = extra_args or []

    # Check standalone commands first (unless a target is provided)
    if cmd in COMMANDS and target is None:
        script, args, _ = COMMANDS[cmd]
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args + extra_args
    elif cmd in PARAM_COMMANDS and target is not None:
        script, arg_template, _ = PARAM_COMMANDS[cmd]
        # Build args: replace None placeholders with the target
        args = []
        for a in arg_template:
            if a is None:
                args.append(target)
            else:
                args.append(a)
        # If target wasn't inserted via None placeholder, append after the flag
        if target not in args:
            args.append(target)
        full_args = [sys.executable, str(SCRIPTS_DIR / script)] + args + extra_args
    elif cmd in PARAM_COMMANDS and target is None:
        _, _, desc = PARAM_COMMANDS[cmd]
        print(f"Error: '{cmd}' requires a target ID.", file=sys.stderr)
        print(f"Usage: python scripts/run.py {cmd} <entry-id>", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Unknown command: '{cmd}'", file=sys.stderr)
        print("Run 'python scripts/run.py --help' for available commands.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(full_args)
    sys.exit(result.returncode)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()
    rest = sys.argv[2:]

    target = None
    extra_args = rest

    # If a command supports parameterized mode and the first arg is positional,
    # treat it as target ID and pass remaining args through.
    if cmd in PARAM_COMMANDS and rest and not rest[0].startswith("-"):
        target = rest[0]
        extra_args = rest[1:]

    # For standalone-only commands, all trailing args are passthrough flags/args.
    if cmd in COMMANDS and cmd not in PARAM_COMMANDS:
        target = None
        extra_args = rest

    run_command(cmd, target, extra_args)


if __name__ == "__main__":
    main()
