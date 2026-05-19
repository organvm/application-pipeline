
# ═══════════════════════════════════════════════════════════
# SECTION 2: SCRIPTS/ — 171 Python Files (19 Categories)
# ═══════════════════════════════════════════════════════════

  # --- Pipeline Library Modules (shared foundation, 8 files) ---
  - id: "FILE-100"
    path: "scripts/pipeline_lib.py"
    type: source
    thread_id: "THR-003"
    title: "Pipeline Library — Shared Foundation"
    summary: "Core shared library imported by every script: load_entries(), load_profile(), load_block(), path constants, ID maps"
    notes: "The single most important file. Every script imports this. Contains PROFILE_ID_MAP and LEGACY_ID_MAP. Decomposed into pipeline_entry_state.py, pipeline_freshness.py, pipeline_market.py."
    tags: [core, library, foundation, shared]
    depends_on: ["FILE-101", "FILE-102", "FILE-103"]
    created: "2026-02-23T16:54:22-05:00"

  - id: "FILE-101"
    path: "scripts/pipeline_entry_state.py"
    type: source
    thread_id: "THR-003"
    title: "Pipeline Entry State Machine"
    summary: "Entry state machine: status transitions, validation, actionable checks"
    notes: "Extracted from pipeline_lib.py. Enforces forward-only progression."
    tags: [state-machine, pipeline, extracted]
    created: "2026-03-26"

  - id: "FILE-102"
    path: "scripts/pipeline_freshness.py"
    type: source
    thread_id: "THR-003"
    title: "Pipeline Freshness Module"
    summary: "Staleness thresholds, age categorization, freshness scoring"
    notes: "Stale=14 days, stagnant=30 days."
    tags: [freshness, staleness, extracted]
    created: "2026-03-26"

  - id: "FILE-103"
    path: "scripts/pipeline_market.py"
    type: source
    thread_id: "THR-003"
    title: "Pipeline Market Intelligence Loader"
    summary: "Market intelligence loader, portal friction scores, HTTP retry"
    tags: [market, intelligence, extracted]
    created: "2026-03-26"

  - id: "FILE-104"
    path: "scripts/standup_constants.py"
    type: source
    thread_id: "THR-005"
    title: "Standup Constants"
    summary: "Standup section names, colors, budget defaults"
    tags: [constants, standup, extracted]
    created: "2026-03-26"

  - id: "FILE-105"
    path: "scripts/standup_work_sections.py"
    type: source
    thread_id: "THR-005"
    title: "Standup Work Sections"
    summary: "Work-focused standup sections: stale, plan, outreach, practices, replenish, deferred, precision compliance"
    tags: [sections, standup, work, extracted]
    created: "2026-03-26"

  - id: "FILE-106"
    path: "scripts/standup_relationship_sections.py"
    type: source
    thread_id: "THR-005"
    title: "Standup Relationship Sections"
    summary: "Relationship standup sections: follow-up dashboard, CRM summary"
    tags: [sections, standup, relationships, extracted]
    created: "2026-03-26"

  - id: "FILE-107"
    path: "scripts/standup_pipeline_sections.py"
    type: source
    thread_id: "THR-005"
    title: "Standup Pipeline Sections"
    summary: "Pipeline-specific standup sections"
    tags: [sections, standup, pipeline, extracted]
    created: "2026-03-26"

  # --- Core Pipeline (33 files) ---
  - id: "FILE-110"
    path: "scripts/apply.py"
    type: source
    thread_id: "THR-015"
    title: "Apply — Single-Command Application Generator"
    summary: "Main application package generator: clearance gate, standards audit, Greenhouse API, answer generation, cover letters, overlap check, PDF build, continuity test"
    notes: "The canonical entry point. Runs the full 10-step pipeline. Created during S35 session."
    tags: [core, application, generator, pipeline]
    depends_on: ["FILE-100", "FILE-130", "FILE-140", "FILE-141"]
    created: "2026-03-25T22:26:03-04:00"

  - id: "FILE-111"
    path: "scripts/apply_engine.py"
    type: source
    thread_id: "THR-015"
    title: "Apply Engine — Extended Application Logic"
    summary: "Alternate/extended apply engine"
    tags: [core, application, engine]
    created: "2026-03-25"

  - id: "FILE-112"
    path: "scripts/advance.py"
    type: source
    thread_id: "THR-004"
    title: "Advance — Forward-Only Status Progression"
    summary: "Enforces forward-only pipeline state progression with validation and outreach evidence requirements"
    notes: "Requires >=1 outreach action before advancing to submitted. 24h freshness gate added 2026-04-22."
    tags: [state-machine, advancement, validation]
    created: "2026-02-23"

  - id: "FILE-113"
    path: "scripts/score.py"
    type: source
    thread_id: "THR-004"
    title: "Score — Multi-Dimensional Scoring Rubric"
    summary: "Three-pillar scoring dispatch: weights_job, weights_grant, weights_consulting. 9 scoring dimensions"
    notes: "Minimum score 7.0 to apply. Dispatches by track to score_* dimension modules."
    tags: [scoring, rubric, three-pillar]
    depends_on: ["FILE-200", "FILE-201", "FILE-202", "FILE-203", "FILE-204"]
    created: "2026-02-23"

  - id: "FILE-114"
    path: "scripts/standup.py"
    type: source
    thread_id: "THR-005"
    title: "Standup — Daily Pipeline Report"
    summary: "Generates daily standup with stale entries, plan, outreach, practices, deferred, precision compliance"
    notes: "Dual-track: work sections + relationship sections."
    tags: [daily, standup, report]
    depends_on: ["FILE-104", "FILE-105", "FILE-106", "FILE-107"]
    created: "2026-02-23T16:35:15-05:00"

  - id: "FILE-115"
    path: "scripts/campaign.py"
    type: source
    thread_id: "THR-006"
    title: "Campaign — Orchestration Engine"
    summary: "Campaign orchestration for batch application preparation"
    notes: "Imports from enrich.py."
    tags: [campaign, orchestration, batch]
    created: "2026-02-23T18:41:35-05:00"

  - id: "FILE-116"
    path: "scripts/run.py"
    type: source
    thread_id: "THR-001"
    title: "Run — Quick-Alias Command Runner"
    summary: "Quick-alias command dispatcher for all pipeline scripts"
    tags: [cli, dispatcher, commands]
    created: "2026-02-23"

  - id: "FILE-117"
    path: "scripts/draft.py"
    type: source
    thread_id: "THR-007"
    title: "Draft — Profile/Block Composition"
    summary: "Drafts application content from blocks, profiles, or legacy scripts with fallback chain"
    notes: "Fallback: blocks -> profile content -> legacy scripts."
    tags: [composition, drafting, blocks]
    created: "2026-02-23"

  - id: "FILE-118"
    path: "scripts/compose.py"
    type: source
    thread_id: "THR-007"
    title: "Compose — Block-Based Content Assembly"
    summary: "Composes application content from modular narrative blocks"
    tags: [composition, blocks, assembly]
    created: "2026-02-23"

  - id: "FILE-119"
    path: "scripts/submit.py"
    type: source
    thread_id: "THR-008"
    title: "Submit — Application Submission"
    summary: "Records submission with metrics checking and outcome logging"
    notes: "Imports from check_metrics.py."
    tags: [submission, recording, metrics]
    created: "2026-02-23T18:10:23-05:00"

  - id: "FILE-120"
    path: "scripts/preflight.py"
    type: source
    thread_id: "THR-008"
    title: "Preflight — Batch Submission Readiness"
    summary: "Checks batch submission readiness across all staged entries"
    tags: [preflight, validation, batch]
    created: "2026-02-23T18:10:23-05:00"

  - id: "FILE-121"
    path: "scripts/quicklog.py"
    type: source
    thread_id: "THR-008"
    title: "Quicklog — Rapid Submission Logging"
    summary: "Quick submission logging with --org, --role, --date flags"
    notes: "Standalone dispatcher added 2026-04-02."
    tags: [logging, quick, submission]
    created: "2026-02-23"

  - id: "FILE-122"
    path: "scripts/enrich.py"
    type: source
    thread_id: "THR-006"
    title: "Enrich — External Data Cascade"
    summary: "Enriches pipeline entries with external data"
    tags: [enrichment, external-data, cascade]
    created: "2026-02-23T18:41:35-05:00"

  - id: "FILE-123"
    path: "scripts/enrich_prestige.py"
    type: source
    thread_id: "THR-006"
    title: "Enrich Prestige — Organizational Prestige Scoring"
    summary: "Prestige enrichment for pipeline entries"
    tags: [prestige, enrichment, scoring]
    created: "2026-02-23"

  - id: "FILE-124"
    path: "scripts/cli.py"
    type: source
    thread_id: "THR-002"
    title: "CLI — Typer Interface"
    summary: "Typer-based CLI interface for pipeline commands"
    tags: [cli, typer, interface]
    created: "2026-02-23"

  - id: "FILE-125"
    path: "scripts/morning.py"
    type: source
    thread_id: "THR-009"
    title: "Morning — Daily Digest Orchestrator"
    summary: "Morning digest: health + stale + followups + campaign"
    tags: [daily, morning, digest, orchestration]
    created: "2026-02-24"

  - id: "FILE-126"
    path: "scripts/pipeline_status.py"
    type: source
    thread_id: "THR-009"
    title: "Pipeline Status — Status Report"
    summary: "Generates pipeline status report"
    tags: [status, report, pipeline]
    created: "2026-02-24"

  - id: "FILE-127"
    path: "scripts/pipeline_mode.py"
    type: source
    thread_id: "THR-009"
    title: "Pipeline Mode — Mode Selection"
    summary: "Selects and manages pipeline operating modes"
    tags: [mode, selection, pipeline]
    created: "2026-02-24"

  - id: "FILE-128"
    path: "scripts/pipeline_api.py"
    type: source
    thread_id: "THR-003"
    title: "Pipeline API — API Layer"
    summary: "API layer for pipeline operations"
    tags: [api, layer, operations]
    created: "2026-02-24"

  - id: "FILE-129"
    path: "scripts/okr.py"
    type: source
    thread_id: "THR-009"
    title: "OKR — Objective Key Result Tracking"
    summary: "Tracks OKRs for pipeline goals"
    tags: [okr, tracking, goals]
    created: "2026-02-24"

  - id: "FILE-130"
    path: "scripts/velocity.py"
    type: source
    thread_id: "THR-009"
    title: "Velocity — Velocity Tracking"
    summary: "Tracks pipeline velocity and throughput"
    tags: [velocity, tracking, throughput]
    created: "2026-02-24"

  - id: "FILE-131"
    path: "scripts/velocity_report.py"
    type: source
    thread_id: "THR-009"
    title: "Velocity Report — Velocity Reporting"
    summary: "Generates velocity reports"
    tags: [velocity, report, performance]
    created: "2026-02-24"

  - id: "FILE-132"
    path: "scripts/retrospective.py"
    type: source
    thread_id: "THR-009"
    title: "Retrospective — Pipeline Retrospective"
    summary: "Generates retrospective analysis"
    tags: [retrospective, analysis, review]
    created: "2026-02-24"

  - id: "FILE-133"
    path: "scripts/prepare_submission.py"
    type: source
    thread_id: "THR-008"
    title: "Prepare Submission — Submission Preparation"
    summary: "Prepares submissions for final review"
    tags: [submission, preparation, review]
    created: "2026-02-23"

  - id: "FILE-134"
    path: "scripts/submit_ready.py"
    type: source
    thread_id: "THR-008"
    title: "Submit Ready — Readiness Check"
    summary: "Checks if submissions are ready"
    tags: [submission, readiness, check]
    created: "2026-02-23"

  - id: "FILE-135"
    path: "scripts/batch_submit.py"
    type: source
    thread_id: "THR-008"
    title: "Batch Submit — Batch Submission"
    summary: "Submits multiple applications in batch"
    tags: [submission, batch, automation]
    created: "2026-02-23"

  - id: "FILE-136"
    path: "scripts/unblock_submissions.py"
    type: source
    thread_id: "THR-008"
    title: "Unblock Submissions — Stuck Submission Resolution"
    summary: "Unblocks stuck submissions"
    tags: [submission, unblock, resolution]
    created: "2026-02-23"

  - id: "FILE-137"
    path: "scripts/archive_research.py"
    type: source
    thread_id: "THR-019"
    title: "Archive Research — Research Entry Archival"
    summary: "Archives research pool entries"
    tags: [archive, research, cleanup]
    created: "2026-02-23"

  - id: "FILE-138"
    path: "scripts/answer_questions.py"
    type: source
    thread_id: "THR-011"
    title: "Answer Questions — ATS Question Answer Generation"
    summary: "Generates answers for ATS portal custom questions"
    tags: [answers, ats, generation]
    created: "2026-02-24"

  - id: "FILE-139"
    path: "scripts/match_engine.py"
    type: source
    thread_id: "THR-007"
    title: "Match Engine — Job-Candidate Matching"
    summary: "Engine for matching candidates to jobs"
    tags: [matching, engine, jobs]
    created: "2026-02-24"

  # --- ATS Portal Submitters (9 files) ---
  - id: "FILE-140"
    path: "scripts/ats_base.py"
    type: source
    thread_id: "THR-010"
    title: "ATS Base — Portal Submission Base Class"
    summary: "Abstract base class for ATS portal submissions"
    tags: [ats, base-class, portal]
    created: "2026-02-24T18:54:18-05:00"

  - id: "FILE-141"
    path: "scripts/greenhouse_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Greenhouse Submit — API Submission"
    summary: "Greenhouse Job Board API submission with custom question answers"
    notes: "Answers from .greenhouse-answers/<entry-id>.yaml. Personal info from .submit-config.yaml."
    tags: [ats, greenhouse, api, submission]
    created: "2026-02-24"

  - id: "FILE-142"
    path: "scripts/greenhouse_browser_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Greenhouse Browser Submit — Playwright Automation"
    summary: "Browser-based Greenhouse submission via Playwright"
    tags: [ats, greenhouse, browser, playwright]
    created: "2026-02-24"

  - id: "FILE-143"
    path: "scripts/lever_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Lever Submit — ATS Portal Submission"
    summary: "Lever ATS submission module"
    tags: [ats, lever, submission]
    created: "2026-02-24T18:54:18-05:00"

  - id: "FILE-144"
    path: "scripts/ashby_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Ashby Submit — ATS Portal Submission"
    summary: "Ashby ATS submission module"
    tags: [ats, ashby, submission]
    created: "2026-02-24T18:54:18-05:00"

  - id: "FILE-145"
    path: "scripts/browser_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Browser Submit — Generic Browser Automation"
    summary: "Generic browser-based submission base class"
    tags: [ats, browser, base-class]
    created: "2026-02-24"

  - id: "FILE-146"
    path: "scripts/ats_verification.py"
    type: source
    thread_id: "THR-010"
    title: "ATS Verification — Portal Field Validation"
    summary: "Verifies ATS portal fields and submission integrity"
    tags: [ats, verification, validation]
    created: "2026-02-24"

  - id: "FILE-147"
    path: "scripts/email_submit.py"
    type: source
    thread_id: "THR-010"
    title: "Email Submit — Email-Based Submission"
    summary: "Email-based submission for non-ATS applications"
    tags: [email, submission, non-ats]
    created: "2026-02-24"

  - id: "FILE-148"
    path: "scripts/scrape_portal.py"
    type: source
    thread_id: "THR-010"
    title: "Scrape Portal — Job Posting Extraction"
    summary: "Scrapes job posting pages for requirements"
    tags: [scraping, portal, extraction]
    created: "2026-02-24"

  # --- Composition & Resume (7 files) ---
  - id: "FILE-150"
    path: "scripts/alchemize.py"
    type: source
    thread_id: "THR-011"
    title: "Alchemize — Greenhouse End-to-End Synthesis"
    summary: "Full Greenhouse synthesis: scrape -> map identity blocks -> generate prompt -> integrate AI output"
    notes: "Generalized beyond Greenhouse 2026-02-24. Imports from greenhouse_submit.py."
    tags: [composition, alchemy, greenhouse, synthesis]
    created: "2026-02-24T18:14:44-05:00"

  - id: "FILE-151"
    path: "scripts/tailor_resume.py"
    type: source
    thread_id: "THR-012"
    title: "Tailor Resume — Target-Specific Resume Generation"
    summary: "Generates tailored resumes in batch-03/ from base templates"
    notes: "All resumes must be exactly 1 page. Current batch: batch-03/ with 45 subdirectories."
    tags: [resume, tailoring, batch]
    created: "2026-02-24T20:05:30-05:00"

  - id: "FILE-152"
    path: "scripts/build_resumes.py"
    type: source
    thread_id: "THR-012"
    title: "Build Resumes — PDF Generation via Headless Chrome"
    summary: "Builds PDF resumes from HTML using headless Chrome"
    tags: [resume, pdf, chrome, build]
    created: "2026-02-24"

  - id: "FILE-153"
    path: "scripts/build_cover_letters.py"
    type: source
    thread_id: "THR-012"
    title: "Build Cover Letters — Cover Letter Generation"
    summary: "Generates cover letters from variants, unique from resume"
    tags: [cover-letter, generation, composition]
    created: "2026-02-24"

  - id: "FILE-154"
    path: "scripts/upgrade_resumes.py"
    type: source
    thread_id: "THR-012"
    title: "Upgrade Resumes — Resume Migration"
    summary: "Migrates and upgrades resume templates"
    tags: [resume, migration, upgrade]
    created: "2026-02-24"

  - id: "FILE-155"
    path: "scripts/review_entry.py"
    type: source
    thread_id: "THR-007"
    title: "Review Entry — Application Entry Review"
    summary: "Reviews pipeline entries for completeness"
    tags: [review, entry, quality]
    created: "2026-02-24"

  - id: "FILE-156"
    path: "scripts/derive_profile.py"
    type: source
    thread_id: "THR-007"
    title: "Derive Profile — Target Profile Generation"
    summary: "Derives target-specific profiles from base identity"
    tags: [profile, derivation, target]
    created: "2026-02-24"

  # --- Scoring Subsystems (10 files) ---
  - id: "FILE-200"
    path: "scripts/score_auto_dimensions.py"
    type: source
    thread_id: "THR-004"
    title: "Score Auto Dimensions — Automated Scoring"
    summary: "Automated dimension scoring"
    tags: [scoring, auto, dimensions]
    created: "2026-02-23"

  - id: "FILE-201"
    path: "scripts/score_human_dimensions.py"
    type: source
    thread_id: "THR-004"
    title: "Score Human Dimensions — Manual Scoring"
    summary: "Human-dimension scoring for subjective criteria"
    tags: [scoring, human, dimensions]
    created: "2026-02-23"

  - id: "FILE-202"
    path: "scripts/score_network.py"
    type: source
    thread_id: "THR-004"
    title: "Score Network — Network Proximity Scoring"
    summary: "Network-based scoring using BFS/DFS path-finding and Granovetter weak-ties hop-decay"
    notes: "Imports from network_graph.py. Referral = 8x hire rate multiplier."
    tags: [scoring, network, proximity]
    depends_on: ["FILE-300"]
    created: "2026-02-23"

  - id: "FILE-203"
    path: "scripts/score_reachability.py"
    type: source
    thread_id: "THR-004"
    title: "Score Reachability — Feasibility Scoring"
    summary: "Reachability scoring based on network paths"
    tags: [scoring, reachability, feasibility]
    created: "2026-02-23"

  - id: "FILE-204"
    path: "scripts/score_text_match.py"
    type: source
    thread_id: "THR-004"
    title: "Score Text Match — TF-IDF Matching"
    summary: "TF-IDF text matching between requirements and profile"
    tags: [scoring, text-match, tfidf]
    created: "2026-02-23"

  - id: "FILE-205"
    path: "scripts/score_constants.py"
    type: source
    thread_id: "THR-004"
    title: "Score Constants — Scoring Configuration"
    summary: "Constant values for scoring rubrics"
    tags: [scoring, constants, config]
    created: "2026-02-23"

  - id: "FILE-206"
    path: "scripts/score_explain.py"
    type: source
    thread_id: "THR-004"
    title: "Score Explain — Score Explanation"
    summary: "Generates human-readable score explanations"
    tags: [scoring, explanation, transparency]
    created: "2026-02-23"

  - id: "FILE-207"
    path: "scripts/score_telemetry.py"
    type: source
    thread_id: "THR-004"
    title: "Score Telemetry — Score Tracking"
    summary: "Tracks scoring telemetry and history"
    tags: [scoring, telemetry, tracking]
    created: "2026-02-23"

  - id: "FILE-208"
    path: "scripts/funding_scorer.py"
    type: source
    thread_id: "THR-004"
    title: "Funding Scorer — Grant/Funding Evaluation"
    summary: "Scoring for grant and funding opportunities"
    tags: [scoring, funding, grants]
    created: "2026-02-24"

  - id: "FILE-209"
    path: "scripts/funding_metrics.py"
    type: source
    thread_id: "THR-004"
    title: "Funding Metrics — Funding Opportunity Analysis"
    summary: "Metrics and analysis for funding opportunities"
    tags: [metrics, funding, analysis]
    created: "2026-02-24"

  # === Diagnostics & Analysis ===

  - id: "FILE-210"
    path: "scripts/diagnose.py"
    type: source
    thread_id: "THR-020"
    title: "Diagnostic Tool — System Self-Assessment"
    summary: "Comprehensive system self-assessment producing a graded scorecard across 9 dimensions using objective collectors and subjective rater prompts"
    tags: [diagnostics, grading, IRA, assessment]
    created: "2026-02-24"

  - id: "FILE-211"
    path: "scripts/diagnose_ira.py"
    type: source
    thread_id: "THR-020"
    title: "IRA Computation — Inter-Rater Agreement"
    summary: "Computes ICC, Cohen's kappa, Fleiss kappa, and consensus scores from multiple rater JSON files with pure-stdlib implementation"
    tags: [IRA, statistics, agreement, kappa]
    created: "2026-02-24"

  - id: "FILE-212"
    path: "scripts/generate_ratings.py"
    type: source
    thread_id: "THR-020"
    title: "Rating Orchestrator — Multi-Model IRA Sessions"
    summary: "Generates subjective dimension ratings from a diverse AI panel, merges with objective ground truth, and saves rating JSON files for IRA computation"
    tags: [ratings, AI, multi-model, IRA]
    created: "2026-02-24"

  - id: "FILE-213"
    path: "scripts/external_validator.py"
    type: source
    thread_id: "THR-020"
    title: "External Validator — Public API Validation"
    summary: "Fetches salary data from BLS OES, skill demand from free job APIs, and org signals from GitHub; stores results in validation cache and compares against scoring constants"
    tags: [validation, BLS, GitHub, external-data]
    created: "2026-02-24"

  - id: "FILE-214"
    path: "scripts/standards.py"
    type: source
    thread_id: "THR-020"
    title: "Standards Framework — Hierarchical Validation"
    summary: "Five-level oversight architecture with triad regulators (3 gates per level, ≥2/3 quorum); wraps existing validators and adds Level 4-5 assessment gates"
    tags: [standards, oversight, quorum, validation]
    created: "2026-02-24"

  - id: "FILE-215"
    path: "scripts/audit_system.py"
    type: source
    thread_id: "THR-020"
    title: "System Audit — Integrity Verification"
    summary: "Verifies statistical claims trace to named sources, rubric-to-code cross-references are wired, and hardcoded values are logically sound"
    tags: [audit, claims, wiring, consistency]
    created: "2026-02-24"

  - id: "FILE-216"
    path: "scripts/verify_all.py"
    type: source
    thread_id: "THR-020"
    title: "Verification Gates — End-to-End Checks"
    summary: "Runs end-to-end verification gates for the repository including lint, validation, pytest, and verification matrix in default or quick mode"
    tags: [verification, CI, gates, quality]
    created: "2026-02-24"

  - id: "FILE-217"
    path: "scripts/verify_canonical.py"
    type: source
    thread_id: "THR-020"
    title: "Canonical Verification — Metrics Drift Detection"
    summary: "Verifies CANONICAL metrics in recruiter_filter.py match actual system state via GitHub API repo counts and filesystem CI/CD workflow counts"
    tags: [canonical, metrics, drift, GitHub-API]
    created: "2026-02-24"

  - id: "FILE-218"
    path: "scripts/verification_matrix.py"
    type: source
    thread_id: "THR-020"
    title: "Verification Matrix — Module Coverage"
    summary: "Ensures every top-level script module has an explicit verification route via direct test file or override evidence in module-verification-overrides.yaml"
    tags: [coverage, modules, verification, testing]
    created: "2026-02-24"

  - id: "FILE-219"
    path: "scripts/validate.py"
    type: source
    thread_id: "THR-020"
    title: "YAML Validator — Schema Compliance"
    summary: "Validates pipeline YAML entries against the schema including required fields, valid statuses, tracks, transitions, portals, and deadline types"
    tags: [validation, schema, YAML, compliance]
    created: "2026-02-24"

  - id: "FILE-220"
    path: "scripts/validate_signals.py"
    type: source
    thread_id: "THR-020"
    title: "Signal Validation — Schema Integrity"
    summary: "Checks signal YAML files (signal-actions, conversion-log, hypotheses, agent-actions) against expected schemas with strict mode support"
    tags: [signals, schema, validation, integrity]
    created: "2026-02-24"

  - id: "FILE-221"
    path: "scripts/validate_hypotheses.py"
    type: source
    thread_id: "THR-020"
    title: "Hypothesis Validation — Prediction vs Actual"
    summary: "Compares predicted vs actual outcomes from hypotheses.yaml cross-referenced against conversion-log.yaml; calculates accuracy by category"
    tags: [hypotheses, validation, accuracy, predictions]
    created: "2026-02-24"

  # === Reporting & Analytics ===

  - id: "FILE-222"
    path: "scripts/funnel_report.py"
    type: source
    thread_id: "THR-021"
    title: "Funnel Analytics — Conversion by Variable"
    summary: "Calculates conversion rates segmented by channel, resume variant, cover letter presence, follow-up count, identity position, and portal type"
    tags: [funnel, conversion, analytics, segmentation]
    created: "2026-02-24"

  - id: "FILE-223"
    path: "scripts/conversion_report.py"
    type: source
    thread_id: "THR-021"
    title: "Conversion Report — Rate Analysis"
    summary: "Analyzes conversion rates by track, identity position, and framing with grouped outcome statistics"
    tags: [conversion, rates, tracking, analysis]
    created: "2026-02-24"

  - id: "FILE-224"
    path: "scripts/conversion_dashboard.py"
    type: source
    thread_id: "THR-021"
    title: "Conversion Dashboard — Unified Intelligence"
    summary: "Combines funnel analytics, outcome learning calibration, and hypothesis pattern analysis into a single actionable report for holistic pipeline performance"
    tags: [dashboard, unified, conversion, intelligence]
    created: "2026-02-24"

  - id: "FILE-225"
    path: "scripts/quarterly_report.py"
    type: source
    thread_id: "THR-021"
    title: "Quarterly Report — State of Applications"
    summary: "Generates comprehensive markdown report covering conversion rates, block ROI, network proximity correlation, scoring dimension accuracy, seasonal patterns, and recommendations"
    tags: [quarterly, report, analytics, recommendations]
    created: "2026-02-24"

  - id: "FILE-226"
    path: "scripts/portfolio_analysis.py"
    type: source
    thread_id: "THR-021"
    title: "Portfolio Analysis — Cross-Pipeline Insights"
    summary: "Queries pipeline data to identify which blocks appear in accepted applications, which identity positions convert best, and which channels perform strongest"
    tags: [portfolio, analysis, blocks, positions]
    created: "2026-02-24"

  - id: "FILE-227"
    path: "scripts/portfolio_bridge.py"
    type: source
    thread_id: "THR-021"
    title: "Portfolio Bridge — Case Study Metadata"
    summary: "Bridges portfolio case study metadata with pipeline entries; auto-suggests work samples from portfolio site matching identity position and track keywords"
    tags: [portfolio, bridge, work-samples, matching]
    created: "2026-02-24"

  - id: "FILE-228"
    path: "scripts/phase_analytics.py"
    type: source
    thread_id: "THR-021"
    title: "Phase Analytics — Volume vs Precision"
    summary: "Compares Volume (Phase 1: ~1,725 cold applications) vs Precision (Phase 2: targeted portal applications) strategies with velocity curves"
    tags: [phases, comparison, volume, precision]
    created: "2026-02-24"

  - id: "FILE-229"
    path: "scripts/block_outcomes.py"
    type: source
    thread_id: "THR-021"
    title: "Block Outcomes — Success Correlation"
    summary: "Cross-tabulates block usage against submission outcomes to classify blocks as golden (correlated with acceptance), neutral, or toxic (correlated with rejection)"
    tags: [blocks, outcomes, correlation, classification]
    created: "2026-02-24"

  - id: "FILE-230"
    path: "scripts/block_roi_analysis.py"
    type: source
    thread_id: "THR-021"
    title: "Block ROI — Acceptance Rate per Block"
    summary: "Calculates which blocks appear in accepted vs rejected applications, providing data-driven guidance for block selection in future submissions"
    tags: [blocks, ROI, acceptance, data-driven]
    created: "2026-02-24"

  - id: "FILE-231"
    path: "scripts/block_engagement.py"
    type: source
    thread_id: "THR-021"
    title: "Block Engagement — Read vs Silence Signal"
    summary: "Cross-tabulates block usage against engagement signal (reviewed vs never read) rather than accept/reject, giving actionable signal earlier in the pipeline"
    tags: [blocks, engagement, read, silence]
    created: "2026-02-24"

  - id: "FILE-232"
    path: "scripts/rejection_learner.py"
    type: source
    thread_id: "THR-021"
    title: "Rejection Learner — Failure Analysis"
    summary: "Correlates scoring dimensions, blocks, timing, and identity position with rejection outcomes; generates actionable adjustment recommendations"
    tags: [rejection, learning, dimensions, adjustment]
    created: "2026-02-24"

  - id: "FILE-233"
    path: "scripts/outcome_learner.py"
    type: source
    thread_id: "THR-021"
    title: "Outcome Learner — Scoring Calibration"
    summary: "Analyzes outcomes to calibrate scoring weights by comparing pre-outcome scores with actual results and recommending rubric adjustments"
    tags: [outcomes, calibration, weights, feedback-loop]
    created: "2026-02-24"

  - id: "FILE-234"
    path: "scripts/outcome_risk.py"
    type: source
    thread_id: "THR-021"
    title: "Outcome Risk — Pre-Submit Screening"
    summary: "Trains a lightweight Naive Bayes model on historical entries with outcomes, then estimates submission risk for a target entry"
    tags: [risk, Naive-Bayes, prediction, screening]
    created: "2026-02-24"

  - id: "FILE-235"
    path: "scripts/snapshot.py"
    type: source
    thread_id: "THR-021"
    title: "Daily Snapshot — Metric Trend Tracking"
    summary: "Captures key pipeline metrics for daily trend tracking with 7d/30d/90d window analysis and historical comparison"
    tags: [snapshot, trends, daily, metrics]
    created: "2026-02-24"

  - id: "FILE-236"
    path: "scripts/weekly_brief.py"
    type: source
    thread_id: "THR-021"
    title: "Weekly Brief — Executive Summary"
    summary: "Produces compact weekly brief with pipeline snapshot, submission velocity, readiness blockers, warm intro queue, failure themes, and hypothesis accuracy"
    tags: [weekly, brief, executive, summary]
    created: "2026-02-24"

  # === Network & CRM ===

  - id: "FILE-237"
    path: "scripts/network_graph.py"
    type: source
    thread_id: "THR-022"
    title: "Network Graph — Professional Connections"
    summary: "Models professional connections as a graph with path-finding to target companies; implements Granovetter's weak-ties theory and 3-degree horizon for network_proximity scoring"
    tags: [network, graph, weak-ties, path-finding]
    created: "2026-02-24"

  - id: "FILE-238"
    path: "scripts/crm.py"
    type: source
    thread_id: "THR-022"
    title: "Relationship CRM — Contact Tracking"
    summary: "Tracks contacts, interactions, and relationship strength across organizations; cross-references with pipeline entries to identify coverage gaps"
    tags: [CRM, contacts, relationships, tracking]
    created: "2026-02-24"

  - id: "FILE-239"
    path: "scripts/research_contacts.py"
    type: source
    thread_id: "THR-022"
    title: "Contact Research — Recruiter Identification"
    summary: "Generates structured research prompts for finding hiring contacts and populates follow-up protocol dates relative to submission"
    tags: [contacts, research, recruiter, follow-up]
    created: "2026-02-24"

  - id: "FILE-240"
    path: "scripts/outreach_engine.py"
    type: source
    thread_id: "THR-022"
    title: "Outreach Engine — Auto-Generate Materials"
    summary: "Auto-generates and persists outreach materials for submitted entries, logs actions to outreach-log.yaml, and sets follow-up dates per protocol"
    tags: [outreach, automation, templates, logging]
    created: "2026-02-24"

  - id: "FILE-241"
    path: "scripts/outreach_templates.py"
    type: source
    thread_id: "THR-022"
    title: "Outreach Templates — Message Generation"
    summary: "Generates personalized LinkedIn connect notes, cold emails, and follow-up messages using entry data, identity positions, and block content"
    tags: [templates, LinkedIn, email, personalization]
    created: "2026-02-24"

  - id: "FILE-242"
    path: "scripts/warm_intro_audit.py"
    type: source
    thread_id: "THR-022"
    title: "Warm Intro Audit — Referral Path Discovery"
    summary: "Systematically identifies warm referral paths by analyzing organization density, existing contacts, and referral candidates for the 8x referral multiplier"
    tags: [warm-intro, referrals, audit, network]
    created: "2026-02-24"

  - id: "FILE-243"
    path: "scripts/cultivate.py"
    type: source
    thread_id: "THR-022"
    title: "Cultivation Workflow — Pre-Submission Network Building"
    summary: "Identifies entries where network improvement could push score above threshold, suggests concrete actions, and logs cultivation activity"
    tags: [cultivation, network, improvement, workflow]
    created: "2026-02-24"

  - id: "FILE-244"
    path: "scripts/dm_composer.py"
    type: source
    thread_id: "THR-022"
    title: "DM Composer — Post-Acceptance Messages"
    summary: "Composes post-acceptance LinkedIn DMs satisfying all 7 Protocol articles by building on original connect note hooks and targeting recipient's daily inhabitation"
    tags: [DM, composition, protocol, LinkedIn]
    created: "2026-02-24"

  # === Job Discovery & Sourcing ===

  - id: "FILE-245"
    path: "scripts/source_jobs.py"
    type: source
    thread_id: "THR-023"
    title: "Job Sourcing — ATS API Polling"
    summary: "Polls Greenhouse, Lever, and Ashby job board APIs for matching postings, filters by title keywords, deduplicates, and creates pipeline YAML files in research_pool"
    tags: [sourcing, ATS, APIs, polling]
    created: "2026-02-24"

  - id: "FILE-246"
    path: "scripts/source_jobs_constants.py"
    type: source
    thread_id: "THR-023"
    title: "Sourcing Constants — Title Keywords and Filters"
    summary: "Defines title keywords, exclusions, location classes, and US states for the job sourcing pipeline"
    tags: [constants, keywords, filters, sourcing]
    created: "2026-02-24"

  - id: "FILE-247"
    path: "scripts/discover_jobs.py"
    type: source
    thread_id: "THR-023"
    title: "Job Discovery — Skill-Based Search"
    summary: "Searches Remotive, Himalayas, and The Muse by keywords mapped to identity positions; complements company-locked source_jobs with open-ended skill-based search"
    tags: [discovery, skills, search, free-APIs]
    created: "2026-02-24"

  - id: "FILE-248"
    path: "scripts/generate_job_profile.py"
    type: source
    thread_id: "THR-023"
    title: "Job Profile Generator — Minimal Profile JSONs"
    summary: "Generates minimal profile JSONs for auto-sourced job entries without profiles, unblocking preflight checks that require profile content"
    tags: [profiles, generation, auto-sourced, minimal]
    created: "2026-02-24"

  - id: "FILE-249"
    path: "scripts/ingest_top_roles.py"
    type: source
    thread_id: "THR-023"
    title: "Top Roles Ingestion — Glove-Fit Filtering"
    summary: "Fetches, pre-scores, and surfaces top-tier job matches with identity filter; promotes qualifying entries directly to pipeline/active/ as qualified"
    tags: [ingestion, scoring, filtering, promotion]
    created: "2026-02-24"

  - id: "FILE-250"
    path: "scripts/ingest_historical.py"
    type: source
    thread_id: "THR-023"
    title: "Historical Ingestion — CSV Import"
    summary: "Parses LinkedIn and ApplyAll CSV exports, deduplicates, classifies ATS portals, and writes unified historical-outcomes.yaml for outcome learning"
    tags: [historical, CSV, import, deduplication]
    created: "2026-02-24"

  - id: "FILE-251"
    path: "scripts/refresh_from_ecosystem.py"
    type: source
    thread_id: "THR-023"
    title: "Ecosystem Refresh — Metric Sync"
    summary: "Reads system-snapshot.json from corpus repo and updates config/metrics.yaml with current values; single point of contact with the ORGANVM ecosystem"
    tags: [ecosystem, metrics, sync, corpus]
    created: "2026-02-24"

  - id: "FILE-252"
    path: "scripts/github_proximity.py"
    type: source
    thread_id: "THR-023"
    title: "GitHub Proximity — Interaction Scoring"
    summary: "Scans GitHub events via gh CLI to update contacts with proximity scores based on stars, forks, comments, reviews, and PR activity"
    tags: [GitHub, proximity, interactions, scoring]
    created: "2026-02-24"

  # === Market Intelligence ===

  - id: "FILE-253"
    path: "scripts/market_intel.py"
    type: source
    thread_id: "THR-024"
    title: "Market Intelligence — Research Summary"
    summary: "Reads strategy/market-intelligence-2026.json and presents structured summaries for track benchmarks, grant calendar, salary data, skills signals, and channel multipliers"
    tags: [market, intelligence, benchmarks, calendar]
    created: "2026-02-24"

  - id: "FILE-254"
    path: "scripts/org_intelligence.py"
    type: source
    thread_id: "THR-024"
    title: "Organization Intelligence — Aggregate Data"
    summary: "Ranks organizations by composite opportunity score combining entry outcomes, contact density, response times, and historical conversion rates"
    tags: [organizations, ranking, intelligence, composite]
    created: "2026-02-24"

  - id: "FILE-255"
    path: "scripts/skills_gap.py"
    type: source
    thread_id: "THR-024"
    title: "Skills Gap — Requirement vs Coverage"
    summary: "Compares required skills from job postings against portfolio content coverage using TF-IDF tokenizer to identify skill gaps"
    tags: [skills, gap, TF-IDF, coverage]
    created: "2026-02-24"

  - id: "FILE-256"
    path: "scripts/text_match.py"
    type: source
    thread_id: "THR-024"
    title: "Text Match — TF-IDF Cosine Similarity"
    summary: "Computes TF-IDF cosine similarity between job posting text and candidate content (blocks, resumes, profiles) using pure stdlib Python"
    tags: [TF-IDF, cosine, similarity, matching]
    created: "2026-02-24"

  # === Communication & Outreach ===

  - id: "FILE-257"
    path: "scripts/linkedin_composer.py"
    type: source
    thread_id: "THR-025"
    title: "LinkedIn Composer — Content Engine"
    summary: "Audits, manages, and composes LinkedIn posts with Testament discipline; validates drafts against 13 articles, tracks posting history, and plans next post"
    tags: [LinkedIn, content, Testament, composition]
    created: "2026-02-24"

  - id: "FILE-258"
    path: "scripts/log_dm.py"
    type: source
    thread_id: "THR-025"
    title: "DM Logger — Three-File Atomic Update"
    summary: "Logs a DM to all three signal files (contacts.yaml, outreach-log.yaml, network.yaml) atomically, solving the three-file update gap"
    tags: [DM, logging, atomic, signals]
    created: "2026-02-24"

  - id: "FILE-259"
    path: "scripts/hydrate_followups.py"
    type: source
    thread_id: "THR-025"
    title: "Followup Hydration — Batch Field Population"
    summary: "Batch-hydrates follow_up fields on submitted pipeline entries with protocol-based follow-up schedules and overdue detection"
    tags: [followups, hydration, batch, protocol]
    created: "2026-02-24"

  - id: "FILE-260"
    path: "scripts/followup.py"
    type: source
    thread_id: "THR-025"
    title: "Followup Tracker — Daily Outreach List"
    summary: "Tracks follow-up dates per submitted entry, generates daily action lists, and logs outreach activity to signals/outreach-log.yaml"
    tags: [followups, tracking, daily, outreach]
    created: "2026-02-24"

  - id: "FILE-261"
    path: "scripts/notify.py"
    type: source
    thread_id: "THR-025"
    title: "Notification Dispatcher — Event Routing"
    summary: "Routes pipeline events to configured channels supporting webhook (POST JSON) and email (SMTP) delivery based on notifications.yaml configuration"
    tags: [notifications, webhook, email, routing]
    created: "2026-02-24"

  - id: "FILE-262"
    path: "scripts/log_signal_action.py"
    type: source
    thread_id: "THR-025"
    title: "Signal Action Logger — Audit Trail"
    summary: "Records when a pipeline signal (hypothesis, score threshold, pattern) triggers a concrete action, creating an auditable feedback loop"
    tags: [signals, actions, audit, feedback]
    created: "2026-02-24"

  # === Pipeline Health & Monitoring ===

  - id: "FILE-263"
    path: "scripts/monitor_pipeline.py"
    type: source
    thread_id: "THR-026"
    title: "Pipeline Monitor — Health Checks"
    summary: "Monitors pipeline health via backup freshness and signal file age checks; designed for scheduled automation (launchd) and manual spot checks"
    tags: [monitoring, health, backup, freshness]
    created: "2026-02-24"

  - id: "FILE-264"
    path: "scripts/daily_pipeline_health.py"
    type: source
    thread_id: "THR-026"
    title: "Daily Health — Composite Job"
    summary: "Runs full daily freshness loop: fetch ATS postings, auto-score/qualify, enrich materials, generate campaign/standup, run hygiene checks, optionally email report"
    tags: [daily, health, composite, automation]
    created: "2026-02-24"

  - id: "FILE-265"
    path: "scripts/daily_pipeline_orchestrator.py"
    type: source
    thread_id: "THR-026"
    title: "Daily Orchestrator — Scan to Outreach"
    summary: "Runs complete daily cycle end-to-end: Scan discovers jobs, Match scores them, Build generates materials, Apply submits, Outreach schedules follow-ups"
    tags: [orchestrator, daily, cycle, automation]
    created: "2026-02-24"

  - id: "FILE-266"
    path: "scripts/scheduler_health.py"
    type: source
    thread_id: "THR-026"
    title: "Scheduler Health — Launchd Audit"
    summary: "Checks each pipeline launchd plist for installation, loading status, and recent execution based on log file freshness"
    tags: [scheduler, launchd, health, audit]
    created: "2026-02-24"

  - id: "FILE-267"
    path: "scripts/freshness_monitor.py"
    type: source
    thread_id: "THR-026"
    title: "Freshness Monitor — Age-Based Categorization"
    summary: "Monitors entry freshness by computing posting age, categorizing into freshness tiers, and optionally checking application URL liveness"
    tags: [freshness, age, categorization, URL-check]
    created: "2026-02-24"

  - id: "FILE-268"
    path: "scripts/check_metrics.py"
    type: source
    thread_id: "THR-026"
    title: "Metrics Checker — Consistency Validation"
    summary: "Validates metric consistency across block files, profiles, and strategy docs by scanning for number patterns and reporting discrepancies from canonical source"
    tags: [metrics, consistency, validation, canonical]
    created: "2026-02-24"

  - id: "FILE-269"
    path: "scripts/sync_metrics.py"
    type: source
    thread_id: "THR-026"
    title: "Metrics Sync — Covenant-Ark Comparison"
    summary: "Compares canonical metrics in covenant-ark.md against blocks and identity-positions docs to prevent stale number credibility risks"
    tags: [metrics, sync, covenant-ark, staleness]
    created: "2026-02-24"

  - id: "FILE-270"
    path: "scripts/backup_pipeline.py"
    type: source
    thread_id: "THR-026"
    title: "Backup Pipeline — YAML Protection"
    summary: "Creates dated tar.gz backups of pipeline YAML files and commits to git for full audit trail; supports restore from backup"
    tags: [backup, protection, tar.gz, audit]
    created: "2026-02-24"

  # === Calendar & Scheduling ===

  - id: "FILE-271"
    path: "scripts/calendar_export.py"
    type: source
    thread_id: "THR-027"
    title: "Calendar Export — iCal Generation"
    summary: "Generates iCal (.ics) files from pipeline deadlines with 7-day and 1-day alarms, follow-up dates, and scheduled agent runs using pure stdlib"
    tags: [calendar, iCal, deadlines, alarms]
    created: "2026-02-24"

  - id: "FILE-272"
    path: "scripts/launchd_manager.py"
    type: source
    thread_id: "THR-027"
    title: "Launchd Manager — Automation Control"
    summary: "Manages launchd agents for pipeline automation on macOS with install, uninstall, status, and kickstart operations"
    tags: [launchd, macOS, automation, management]
    created: "2026-02-24"

  # === AI Agent & MCP ===

  - id: "FILE-273"
    path: "scripts/agent.py"
    type: source
    thread_id: "THR-028"
    title: "Autonomous Agent — State Machine Execution"
    summary: "Autonomous pipeline agent that reads state, decides actions, and executes based on rules; enables unattended batch processing while maintaining human authority"
    tags: [agent, autonomous, state-machine, execution]
    created: "2026-02-24"

  - id: "FILE-274"
    path: "scripts/mcp_server.py"
    type: source
    thread_id: "THR-028"
    title: "MCP Server — Agentic Pipeline Access"
    summary: "Exposes core pipeline functions (score, advance, draft, validate) as MCP tools using clean API layer for agentic execution without tight coupling"
    tags: [MCP, server, tools, agentic]
    created: "2026-02-24"

  - id: "FILE-275"
    path: "scripts/handoff_seed.py"
    type: source
    thread_id: "THR-028"
    title: "Handoff Seed — Session Ignition"
    summary: "Aggregates system state into a persistent 'soul' for the next session ignition per Protocol SOP-SYS-003"
    tags: [handoff, seed, session, protocol]
    created: "2026-02-24"

  - id: "FILE-276"
    path: "scripts/scan_orchestrator.py"
    type: source
    thread_id: "THR-028"
    title: "Scan Orchestrator — Unified Job Fetch"
    summary: "Combines source_jobs (5 ATS APIs) and discover_jobs (free APIs) into a single scan operation with deduplication, filtering, and logging"
    tags: [scan, orchestration, deduplication, unified]
    created: "2026-02-24"

  # === Hypothesis & Learning ===

  - id: "FILE-277"
    path: "scripts/feedback_capture.py"
    type: source
    thread_id: "THR-029"
    title: "Feedback Capture — Hypothesis Recording"
    summary: "Captures structured outcome hypotheses when outcomes are recorded, enabling pattern analysis once 10+ outcomes exist"
    tags: [feedback, hypotheses, capture, patterns]
    created: "2026-02-24"

  - id: "FILE-278"
    path: "scripts/resolve_hypotheses.py"
    type: source
    thread_id: "THR-029"
    title: "Hypothesis Resolver — Historical Evidence"
    summary: "Auto-resolves outcome hypotheses using historical evidence; validates cold-app hypotheses against 1,469 applications with 0% interview rate"
    tags: [hypotheses, resolution, historical, evidence]
    created: "2026-02-24"

  - id: "FILE-279"
    path: "scripts/recalibrate.py"
    type: source
    thread_id: "THR-029"
    title: "Recalibration — Quarterly Weight Adjustment"
    summary: "Proposes quarterly rubric weight adjustments based on rejection learner insights; requires human approval before any changes are applied"
    tags: [recalibration, weights, quarterly, approval]
    created: "2026-02-24"

  - id: "FILE-280"
    path: "scripts/recalibrate_engagement.py"
    type: source
    thread_id: "THR-029"
    title: "Engagement Recalibration — Read vs Silence"
    summary: "Proposes weight adjustments from engagement signal (read vs silence) rather than accept/reject outcomes, closing feedback loop earlier"
    tags: [recalibration, engagement, read, silence]
    created: "2026-02-24"

  # === Identity & Positioning ===

  - id: "FILE-281"
    path: "scripts/classify_position.py"
    type: source
    thread_id: "THR-030"
    title: "Position Classifier — Auto-Assignment"
    summary: "Auto-classifies identity positions from job titles and descriptions using keyword rules; maps to 9 canonical positions instead of defaulting to independent-engineer"
    tags: [classification, positions, keywords, auto-assign]
    created: "2026-02-24"

  - id: "FILE-282"
    path: "scripts/derive_positions.py"
    type: source
    thread_id: "THR-030"
    title: "Position Derivation — Ecosystem Relevance"
    summary: "Derives identity position relevance from ecosystem activity data; analyzes which organs are most active and suggests best-supported positions"
    tags: [positions, derivation, ecosystem, relevance]
    created: "2026-02-24"

  - id: "FILE-283"
    path: "scripts/corpus_fingerprint.py"
    type: source
    thread_id: "THR-030"
    title: "Corpus Fingerprint — TF-IDF Vector"
    summary: "Creates living TF-IDF vector from all blocks, resumes, and project content; as blocks are added or modified, fingerprint automatically reflects full scope"
    tags: [corpus, fingerprint, TF-IDF, living]
    created: "2026-02-24"

  - id: "FILE-284"
    path: "scripts/generate_id_mappings.py"
    type: source
    thread_id: "THR-030"
    title: "ID Mapping Generator — Filesystem Similarity"
    summary: "Generates profile_id_map and legacy_id_map suggestions from filesystem similarity using difflib for entry-to-profile and legacy-script-to-entry matching"
    tags: [ID-mapping, similarity, difflib, generation]
    created: "2026-02-24"

  # === Blocks & Materials ===

  - id: "FILE-285"
    path: "scripts/build_block_index.py"
    type: source
    thread_id: "THR-031"
    title: "Block Index — Frontmatter Parser"
    summary: "Builds searchable index from block frontmatter; reads all blocks/**/*.md files and writes blocks/_index.yaml with per-block listing and inverted tag_index"
    tags: [blocks, index, frontmatter, search]
    created: "2026-02-24"

  - id: "FILE-286"
    path: "scripts/generate_project_blocks.py"
    type: source
    thread_id: "THR-031"
    title: "Project Block Generator — Repo to Blocks"
    summary: "Generates project blocks for ORGANVM repos from registry, README, and seed data; writes complete blocks/projects/{name}.md with frontmatter and tiered content"
    tags: [blocks, generation, projects, repos]
    created: "2026-02-24"

  - id: "FILE-287"
    path: "scripts/material_builder.py"
    type: source
    thread_id: "THR-031"
    title: "Material Builder — LLM Generation"
    summary: "LLM-powered generation of cover letters, answers, and block selections for qualified entries using google-genai; all outputs saved as drafts requiring human approval"
    tags: [materials, LLM, generation, google-genai]
    created: "2026-02-24"

  - id: "FILE-288"
    path: "scripts/materials_validator.py"
    type: source
    thread_id: "THR-031"
    title: "Materials Validator — Protocol Enforcement"
    summary: "Enforces 12 articles of the Materials Protocol for submission packages (resume + cover letter + portal answers); third in the ORGANVM rhetorical triad"
    tags: [materials, validation, protocol, triad]
    created: "2026-02-24"

  - id: "FILE-289"
    path: "scripts/resume_drift_report.py"
    type: source
    thread_id: "THR-031"
    title: "Resume Drift — Tailored vs Base Comparison"
    summary: "Compares batch-03 tailored resumes against base templates; extracts sections, computes per-section similarity, detects near-duplicate clusters, and reports bullet-label reuse"
    tags: [resume, drift, comparison, similarity]
    created: "2026-02-24"

  # === Protocol & Standards ===

  - id: "FILE-290"
    path: "scripts/protocol_types.py"
    type: source
    thread_id: "THR-032"
    title: "Protocol Types — Domain Dataclasses"
    summary: "Core dataclasses for messages, agents, claims, tensions, questions, and all validation result types used by protocol_validator and dm_composer"
    tags: [types, dataclasses, protocol, domain]
    created: "2026-02-24"

  - id: "FILE-291"
    path: "scripts/protocol_validator.py"
    type: source
    thread_id: "THR-032"
    title: "Protocol Validator — 7 Article Enforcement"
    summary: "Enforces the 7 articles of the Outreach Protocol formal system; validates messages and message sequences against the formal specification"
    tags: [protocol, validation, articles, enforcement]
    created: "2026-02-24"

  - id: "FILE-292"
    path: "scripts/recruiter_filter.py"
    type: source
    thread_id: "THR-032"
    title: "Recruiter Filter — Pre-Submission Gate"
    summary: "Final gate before submission; validates all application materials against canonical metrics, common red flags, and formatting standards from recruiter perspective"
    tags: [recruiter, filter, gate, validation]
    created: "2026-02-24"

  # === Miscellaneous & Utility ===

  - id: "FILE-293"
    path: "scripts/check_email.py"
    type: source
    thread_id: "THR-033"
    title: "Email Checker — Mail.app Integration"
    summary: "Searches Gmail via macOS Mail.app AppleScript for ATS confirmation and response emails; cross-references against submitted pipeline entries"
    tags: [email, Mail.app, AppleScript, ATS]
    created: "2026-02-24"

  - id: "FILE-294"
    path: "scripts/check_email_constants.py"
    type: source
    thread_id: "THR-033"
    title: "Email Constants — ATS Sender Patterns"
    summary: "Defines ATS sender patterns, confirmation regex, interview keywords, and rejection patterns for the email checker"
    tags: [constants, email, patterns, ATS]
    created: "2026-02-24"

  - id: "FILE-295"
    path: "scripts/check_deferred.py"
    type: source
    thread_id: "THR-033"
    title: "Deferred Checker — Re-Activation Readiness"
    summary: "Auto-checks and flags deferred entries ready for re-activation based on resume_date; categorizes by overdue, upcoming, distant, and no-date"
    tags: [deferred, re-activation, readiness, scheduling]
    created: "2026-02-24"

  - id: "FILE-296"
    path: "scripts/check_outcomes.py"
    type: source
    thread_id: "THR-033"
    title: "Outcome Tracker — Response Monitoring"
    summary: "Tracks post-submission outcomes and response times across the pipeline; supports outcome recording, stale alerts, and failure theme extraction"
    tags: [outcomes, tracking, responses, stale]
    created: "2026-02-24"

  - id: "FILE-297"
    path: "scripts/hygiene.py"
    type: source
    thread_id: "THR-033"
    title: "Entry Hygiene — Data Quality Validation"
    summary: "Validates entry freshness and data quality beyond schema validation; checks URL liveness, ATS posting verification, auto-expire, and track-specific gates"
    tags: [hygiene, quality, freshness, validation]
    created: "2026-02-24"

  - id: "FILE-298"
    path: "scripts/traffic_signals.py"
    type: source
    thread_id: "THR-033"
    title: "Traffic Signals — Visitor Engagement"
    summary: "Detects visitor engagement across public properties via GitHub repo traffic and Plausible analytics; correlates with pipeline submissions for follow-up signals"
    tags: [traffic, signals, engagement, correlation]
    created: "2026-02-24"

  - id: "FILE-299"
    path: "scripts/yaml_mutation.py"
    type: source
    thread_id: "THR-033"
    title: "YAML Mutation — Structure-Preserving Edits"
    summary: "Round-trip YAML mutation using ruamel.yaml; replaces regex-based mutations with structure-preserving edits maintaining comments, key ordering, and quoting style"
    tags: [YAML, mutation, ruamel, structure-preserving]
    created: "2026-02-24"

  - id: "FILE-300"
    path: "scripts/submission_audit.py"
    type: source
    thread_id: "THR-033"
    title: "Submission Audit — Readiness Diagnostic"
    summary: "Batch submission readiness diagnostic checking every active entry for portal, resume, cover letter, status, answer files, auth configuration, and answer completeness"
    tags: [audit, submission, readiness, diagnostic]
    created: "2026-02-24"

  # === Infrastructure ===

  - id: "FILE-301"
    path: "scripts/blind_spot_tracker.py"
    type: source
    thread_id: "THR-034"
    title: "Blind Spot Tracker — Startup Profile Actions"
    summary: "Maps startup-profile blind spots to concrete pipeline actions; scores blind spots via funding_scorer and maps incomplete items to actionable next steps"
    tags: [blind-spots, startup, actions, tracking]
    created: "2026-02-24"

  - id: "FILE-302"
    path: "scripts/smart_triage.py"
    type: source
    thread_id: "THR-034"
    title: "Smart Triage — Time-Decay Scoring"
    summary: "Intelligent triage of research-pool entries using time-decay scoring; surfaces top opportunities and auto-archives low-value entries based on composite score"
    tags: [triage, time-decay, scoring, auto-archive]
    created: "2026-02-24"

# ============================================================
# SECTION 3: PIPELINE/ — Application Pipeline YAML Entries
# ============================================================
# State machine: research → qualified → drafting → staged → submitted → acknowledged → interview → outcome
# 20 active, 16 submitted, 1,706 closed, 356 research pool entries (as of 2026-05-19)

## 3.1: Pipeline Schema

  - id: "FILE-303"
    path: "pipeline/_schema.yaml"
    type: config
    thread_id: "THR-035"
    title: "Pipeline Entry Schema — YAML Structure Definition"
    summary: "Canonical schema defining all required and optional fields for pipeline entries including identification, target info, deadline, amount, scoring, submission, and blocks_used sections"
    tags: [schema, yaml, validation, pipeline]
    created: "2026-02-24"

## 3.2: Active Applications (20 entries — all in drafting status)

  - id: "FILE-304"
    path: "pipeline/active/affirm-senior-software-engineer-infrastructure.yaml"
    type: data
    thread_id: "THR-035"
    title: "Affirm Senior Software Engineer (Infrastructure) — Trust Infra Team"
    summary: "Greenhouse portal, US Remote, drafting stage — security infrastructure role covering secrets management, authentication, authorization, and cryptography"
    tags: [job, drafting, greenhouse, security, infrastructure]
    created: "2026-03-01"

  - id: "FILE-305"
    path: "pipeline/active/anduril-salesforce-software-developer.yaml"
    type: data
    thread_id: "THR-035"
    title: "Anduril Salesforce Software Developer — Defense Technology"
    summary: "Greenhouse portal, Costa Mesa CA onsite, drafting stage — Salesforce development for defense systems powered by Lattice OS"
    tags: [job, drafting, greenhouse, defense, salesforce]
    created: "2026-03-01"

  - id: "FILE-306"
    path: "pipeline/active/anthropic-senior-staff-software-engineer-voice-platform.yaml"
    type: data
    thread_id: "THR-035"
    title: "Anthropic Senior/Staff+ Software Engineer, Voice Platform — AI Safety"
    summary: "Greenhouse portal, SF/NYC/Seattle onsite, drafting stage — building safe, interpretable, and steerable AI voice systems"
    tags: [job, drafting, greenhouse, ai, voice]
    created: "2026-03-01"

  - id: "FILE-307"
    path: "pipeline/active/cloudflare-associate-solutions-engineer.yaml"
    type: data
    thread_id: "THR-035"
    title: "Cloudflare Associate Solutions Engineer — Network Infrastructure"
    summary: "Greenhouse portal, Hybrid location, drafting stage — solutions engineering for world's largest CDN network"
    tags: [job, drafting, greenhouse, networking, solutions]
    created: "2026-03-01"

  - id: "FILE-308"
    path: "pipeline/active/coinbase-staff-software-engineer-platform-identity.yaml"
    type: data
    thread_id: "THR-035"
    title: "Coinbase Staff Software Engineer (Platform - Identity) — Crypto Infrastructure"
    summary: "Greenhouse portal, US Remote, drafting stage — building onchain platform identity and access systems"
    tags: [job, drafting, greenhouse, crypto, identity]
    created: "2026-03-01"

  - id: "FILE-309"
    path: "pipeline/active/dbt-labs-senior-developer-experience-advocate.yaml"
    type: data
    thread_id: "THR-035"
    title: "dbt Labs Senior Developer Experience Advocate — Analytics Engineering"
    summary: "Greenhouse portal, US Remote, drafting stage — developer advocacy for analytics engineering platform used by 90,000+ teams"
    tags: [job, drafting, greenhouse, devrel, analytics]
    created: "2026-03-01"

  - id: "FILE-310"
    path: "pipeline/active/elevenlabs-enterprise-solutions-engineer-latam.yaml"
    type: data
    thread_id: "THR-035"
    title: "ElevenLabs Enterprise Solutions Engineer (LATAM) — AI Voice Platform"
    summary: "Ashby portal, Mexico location, drafting stage — enterprise solutions for AI voice platform valued at $11B"
    tags: [job, drafting, ashby, ai-voice, enterprise]
    created: "2026-03-01"

  - id: "FILE-311"
    path: "pipeline/active/gitlab-senior-backend-engineer-ai-pipeline-execution.yaml"
    type: data
    thread_id: "THR-035"
    title: "GitLab Senior Backend Engineer (AI), Pipeline Execution — DevSecOps"
    summary: "Greenhouse portal, multi-region remote, drafting stage — AI-powered DevSecOps orchestration platform"
    tags: [job, drafting, greenhouse, devsecops, backend]
    created: "2026-03-01"

  - id: "FILE-312"
    path: "pipeline/active/google-ami.yaml"
    type: data
    thread_id: "THR-035"
    title: "Google AMI Grants — $10K Art Funding"
    summary: "Custom portal, TBA deadline, drafting stage, grant track — $10,000 USD lump sum, identity position: creative-technologist"
    tags: [grant, drafting, custom, google, art-funding]
    created: "2026-03-01"

  - id: "FILE-313"
    path: "pipeline/active/grafana-labs-partner-solutions-engineer-us-remote.yaml"
    type: data
    thread_id: "THR-035"
    title: "Grafana Labs Partner Solutions Engineer — Observability Platform"
    summary: "Greenhouse portal, US Remote, drafting stage — partner engineering for 20M+ user observability platform"
    tags: [job, drafting, greenhouse, observability, partner]
    created: "2026-03-01"

  - id: "FILE-314"
    path: "pipeline/active/grafana-labs-senior-software-engineer-observability-knowledge-graph-backe.yaml"
    type: data
    thread_id: "THR-035"
    title: "Grafana Labs Senior Software Engineer — Observability Knowledge Graph Backend"
    summary: "Greenhouse portal, Canada Remote, drafting stage — knowledge graph backend for observability data"
    tags: [job, drafting, greenhouse, knowledge-graph, backend]
    created: "2026-03-01"

  - id: "FILE-315"
    path: "pipeline/active/grafana-labs-senior-solutions-engineer-east-coast-remote.yaml"
    type: data
    thread_id: "THR-035"
    title: "Grafana Labs Senior Solutions Engineer — East Coast Remote"
    summary: "Greenhouse portal, US Remote, drafting stage — solutions engineering for LGTM observability stack"
    tags: [job, drafting, greenhouse, observability, solutions]
    created: "2026-03-01"

  - id: "FILE-316"
    path: "pipeline/active/grafana-labs-staff-software-engineer-grafana-cloud-k6-canada-remote.yaml"
    type: data
    thread_id: "THR-035"
    title: "Grafana Labs Staff Software Engineer — Grafana Cloud k6"
    summary: "Greenhouse portal, Canada Remote, drafting stage — load testing platform engineering"
    tags: [job, drafting, greenhouse, load-testing, staff]
    created: "2026-03-01"

  - id: "FILE-317"
    path: "pipeline/active/instacart-senior-software-engineer-ii-page-builder-retailer-platform.yaml"
    type: data
    thread_id: "THR-035"
    title: "Instacart Senior Software Engineer II — Page Builder (Retailer Platform)"
    summary: "Greenhouse portal, Canada Remote, drafting stage — grocery delivery platform engineering"
    tags: [job, drafting, greenhouse, e-commerce, platform]
    created: "2026-03-01"

  - id: "FILE-318"
    path: "pipeline/active/mongodb-senior-software-engineer-atlas-stream-processing.yaml"
    type: data
    thread_id: "THR-035"
    title: "MongoDB Senior Software Engineer — Atlas Stream Processing"
    summary: "Greenhouse portal, NYC onsite, drafting stage — C++ stream processing engine for continuous data processing"
    tags: [job, drafting, greenhouse, streaming, cpp]
    created: "2026-03-01"

  - id: "FILE-319"
    path: "pipeline/active/neo4j-solutions-engineer-india-startup-program.yaml"
    type: data
    thread_id: "THR-035"
    title: "Neo4j Solutions Engineer (India Startup Program) — Graph Intelligence"
    summary: "Greenhouse portal, India Remote, drafting stage — graph intelligence platform for AI systems"
    tags: [job, drafting, greenhouse, graph, startup]
    created: "2026-03-01"

  - id: "FILE-320"
    path: "pipeline/active/samsara-senior-software-engineer-growth.yaml"
    type: data
    thread_id: "THR-035"
    title: "Samsara Senior Software Engineer, Growth — Connected Operations Cloud"
    summary: "Greenhouse portal, US Remote, drafting stage — IoT connected operations platform (NYSE: IOT)"
    tags: [job, drafting, greenhouse, iot, growth]
    created: "2026-03-01"

  - id: "FILE-321"
    path: "pipeline/active/scale-ai-senior-software-engineer.yaml"
    type: data
    thread_id: "THR-035"
    title: "Scale AI Senior Software Engineer — Public Sector Agentic Capabilities"
    summary: "Greenhouse portal, multi-city onsite, drafting stage — agentic AI capabilities for public sector"
    tags: [job, drafting, greenhouse, ai, public-sector]
    created: "2026-03-01"

  - id: "FILE-322"
    path: "pipeline/active/snowflake-senior-security-architect-applied-field-engineering-afe.yaml"
    type: data
    thread_id: "THR-035"
    title: "Snowflake Senior Security Architect — Applied Field Engineering"
    summary: "Ashby portal, NYC onsite, drafting stage — AI-native security architecture for agentic enterprise"
    tags: [job, drafting, ashby, security, data-cloud]
    created: "2026-03-01"

  - id: "FILE-323"
    path: "pipeline/active/stripe-staff-software-engineer-stream-compute.yaml"
    type: data
    thread_id: "THR-035"
    title: "Stripe Staff Software Engineer — Stream Compute"
    summary: "Greenhouse portal, multi-city onsite, drafting stage — financial infrastructure stream processing"
    tags: [job, drafting, greenhouse, fintech, streaming]
    created: "2026-03-01"

## 3.3: Submitted Applications (16 entries)

  - id: "FILE-324"
    path: "pipeline/submitted/cursor-software-engineer-enterprise-platform.yaml"
    type: data
    thread_id: "THR-036"
    title: "Cursor Software Engineer, Enterprise Platform — AI Coding Automation"
    summary: "Cursor-native portal, SF/Remote, submitted stage — building org management, RBAC, audit logs, and compliance for enterprise coding tool"
    tags: [job, submitted, cursor-native, enterprise, iam]
    created: "2026-03-17"

  - id: "FILE-325"
    path: "pipeline/submitted/doppler-staff-full-stack-software-engineer.yaml"
    type: data
    thread_id: "THR-036"
    title: "Doppler Staff Full-Stack Software Engineer — Secrets Management"
    summary: "Ashby portal, US Remote, submitted stage — secrets management platform, 50K+ customers, $1M ARR milestone"
    tags: [job, submitted, ashby, security, fullstack]
    created: "2026-03-17"

  - id: "FILE-326"
    path: "pipeline/submitted/doris-duke-amt.yaml"
    type: data
    thread_id: "THR-036"
    title: "Doris Duke / Mozilla Artists Make Technology Lab — $150K Grant"
    summary: "Custom portal, NYC, acknowledged stage, grant track — $150,000 award, deadline 2026-03-02, identity: creative-technologist"
    tags: [grant, acknowledged, custom, art-tech, 150k]
    created: "2026-02-24"

  - id: "FILE-327"
    path: "pipeline/submitted/gay-lesbian-review.yaml"
    type: data
    thread_id: "THR-036"
    title: "Gay & Lesbian Review — Writing Submission"
    summary: "Custom portal, NYC, submitted stage, writing track — $250 USD fee, identity: community-practitioner"
    tags: [writing, submitted, custom, lgbtq, publication]
    created: "2026-03-17"

  - id: "FILE-328"
    path: "pipeline/submitted/harvey-ai-midseniorstaff-software-engineer-agents.yaml"
    type: data
    thread_id: "THR-036"
    title: "Harvey AI Mid/Senior/Staff Software Engineer, Agents — Legal AI"
    summary: "Ashby portal, NYC onsite, acknowledged stage — agentic AI for legal services, 1000+ customers in 58+ countries"
    tags: [job, acknowledged, ashby, legal-ai, agents]
    created: "2026-03-17"

  - id: "FILE-329"
    path: "pipeline/submitted/langchain-senior-backend-engineer-enterprise-readiness-identity.yaml"
    type: data
    thread_id: "THR-036"
    title: "LangChain Senior Backend Engineer — Enterprise Readiness & Identity"
    summary: "Ashby portal, NYC onsite, acknowledged stage — agent engineering platform, millions of developers"
    tags: [job, acknowledged, ashby, ai-agents, identity]
    created: "2026-03-17"

  - id: "FILE-330"
    path: "pipeline/submitted/logic-magazine.yaml"
    type: data
    thread_id: "THR-036"
    title: "Logic Magazine — Technology Writing"
    summary: "Custom portal, NYC, submitted stage, writing track — $2,000 USD fee, rolling deadline"
    tags: [writing, submitted, custom, tech-journalism, publication]
    created: "2026-03-17"

  - id: "FILE-331"
    path: "pipeline/submitted/mit-tr-wired-aeon.yaml"
    type: data
    thread_id: "THR-036"
    title: "MIT Technology Review / Wired / Aeon — Multi-Publication Pitch"
    summary: "Custom portal, NYC, submitted stage, writing track — $5,000 USD target fee, rolling deadline"
    tags: [writing, submitted, custom, tech-journalism, multi-pub]
    created: "2026-03-17"

  - id: "FILE-332"
    path: "pipeline/submitted/noema-magazine.yaml"
    type: data
    thread_id: "THR-036"
    title: "Noema Magazine — Philosophy & Technology Essay"
    summary: "Email portal, submitted stage, writing track — $3,000 USD fee, identity: creative-technologist"
    tags: [writing, submitted, email, philosophy, publication]
    created: "2026-03-17"

  - id: "FILE-333"
    path: "pipeline/submitted/openai-technical-deployment-lead-forward-deployed-engineering-fde-n.yaml"
    type: data
    thread_id: "THR-036"
    title: "OpenAI Technical Deployment Lead — Forward Deployed Engineering"
    summary: "Ashby portal, NYC onsite, acknowledged stage — deploying complex AI systems to customers"
    tags: [job, acknowledged, ashby, ai, deployment]
    created: "2026-03-17"

  - id: "FILE-334"
    path: "pipeline/submitted/render-software-engineer-billing.yaml"
    type: data
    thread_id: "THR-036"
    title: "Render Software Engineer, Billing — Cloud Platform"
    summary: "Ashby portal, US Remote, submitted stage — usage-based billing systems, $257M Series C, 4.5M+ developers"
    tags: [job, submitted, ashby, billing, cloud]
    created: "2026-03-17"

  - id: "FILE-335"
    path: "pipeline/submitted/stripe-software-engineer-smart-contract-bridge.yaml"
    type: data
    thread_id: "THR-036"
    title: "Stripe Software Engineer — Smart Contract, Bridge (Stablecoins)"
    summary: "Greenhouse portal, SF/NYC onsite, acknowledged stage — stablecoin payments platform, borderless USD access"
    tags: [job, acknowledged, greenhouse, stablecoin, fintech]
    created: "2026-03-17"

  - id: "FILE-336"
    path: "pipeline/submitted/tailscale-go-core-client-engineer.yaml"
    type: data
    thread_id: "THR-036"
    title: "Tailscale Go Core Client Engineer — Secure Networking"
    summary: "Greenhouse portal, US Remote, submitted stage — WireGuard-based secure interconnect, $163K-$226K range"
    tags: [job, submitted, greenhouse, go, networking]
    created: "2026-03-17"

  - id: "FILE-337"
    path: "pipeline/submitted/temporal-senior-software-engineer-open-source-server.yaml"
    type: data
    thread_id: "THR-036"
    title: "Temporal Senior Software Engineer — Open Source Server"
    summary: "Greenhouse portal, US Remote, acknowledged stage — open source workflow orchestration platform"
    tags: [job, acknowledged, greenhouse, open-source, workflows]
    created: "2026-03-17"

  - id: "FILE-338"
    path: "pipeline/submitted/toast-senior-backend-engineer.yaml"
    type: data
    thread_id: "THR-036"
    title: "Toast Senior Backend Engineer — Restaurant Technology"
    summary: "Greenhouse portal, US Remote, submitted stage — restaurant POS platform, orders and subscriptions team"
    tags: [job, submitted, greenhouse, restaurant, backend]
    created: "2026-03-17"

  - id: "FILE-339"
    path: "pipeline/submitted/webflow-senior-forward-deployed-engineer.yaml"
    type: data
    thread_id: "THR-036"
    title: "Webflow Senior Forward Deployed Engineer — AI-Native DXP"
    summary: "Greenhouse portal, US Remote, acknowledged stage — AI-native Digital Experience Platform"
    tags: [job, acknowledged, greenhouse, web, fde]
    created: "2026-03-17"

## 3.4: Closed Applications (1,706 entries — representative sample)

  - id: "FILE-340"
    path: "pipeline/closed/"
    type: data
    thread_id: "THR-037"
    title: "Closed Applications Archive — 1,706 Historical Entries"
    summary: "Directory of 1,706 completed pipeline entries across all tracks (job, grant, writing, residency) with terminal outcomes (accepted, rejected, withdrawn, expired)"
    tags: [archive, historical, closed, pipeline-data]
    created: "2025-09-01"

  - id: "FILE-341"
    path: "pipeline/closed/affirm-enterprise-iam-software-engineer-ii.yaml"
    type: data
    thread_id: "THR-037"
    title: "Affirm Enterprise IAM Software Engineer II — Identity Access"
    summary: "Closed entry — enterprise IAM engineering at buy-now-pay-later fintech"
    tags: [job, closed, iam, affirm, fintech]
    created: "2025-10-01"

  - id: "FILE-342"
    path: "pipeline/closed/airbyte-software-engineer-applied-ai.yaml"
    type: data
    thread_id: "THR-037"
    title: "Airbyte Software Engineer, Applied AI — Data Integration"
    summary: "Closed entry — applied AI for data integration platform"
    tags: [job, closed, ai, data-integration, airbyte]
    created: "2025-10-15"

  - id: "FILE-343"
    path: "pipeline/closed/anduril-afsim-operations-analyst-mission-engineering-air-dominance-s.yaml"
    type: data
    thread_id: "THR-037"
    title: "Anduril AFSIM Operations Analyst — Mission Engineering"
    summary: "Closed entry — defense simulation operations analysis"
    tags: [job, closed, defense, simulation, anduril]
    created: "2025-11-01"

## 3.5: Research Pool (356 entries — representative sample)

  - id: "FILE-344"
    path: "pipeline/research_pool/"
    type: data
    thread_id: "THR-038"
    title: "Research Pool — 356 Candidate Entries"
    summary: "Directory of 356 auto-sourced research candidates awaiting triage; separate from actionable pipeline entries"
    tags: [research, pool, candidates, sourcing]
    created: "2025-09-01"

  - id: "FILE-345"
    path: "pipeline/research_pool/affirm-senior-software-engineer-fullstack-consumer-engineering.yaml"
    type: data
    thread_id: "THR-038"
    title: "Affirm Senior Software Engineer, Fullstack Consumer Engineering"
    summary: "Research pool entry — fullstack consumer engineering at fintech"
    tags: [research, fullstack, consumer, affirm]
    created: "2026-01-15"

  - id: "FILE-346"
    path: "pipeline/research_pool/anthropic-applied-ai-engineer-startups-2026-03.yaml"
    type: data
    thread_id: "THR-038"
    title: "Anthropic Applied AI Engineer, Startups — AI Safety Research"
    summary: "Research pool entry — applied AI engineering for startup ecosystem"
    tags: [research, ai, startups, anthropic]
    created: "2026-03-01"

# ============================================================
# SECTION 4: SIGNALS/ — CRM & Pipeline Signals
# ============================================================
# Signal files track relationships, outreach, conversions, hypotheses, and agent activity

  - id: "FILE-347"
    path: "signals/contacts.yaml"
    type: data
    thread_id: "THR-039"
    title: "CRM Contacts — Relationship Database"
    summary: "Contact relationship database with organization, role, channel, relationship strength, LinkedIn URLs, and interaction history (93KB, last modified 2026-04-14)"
    tags: [crm, contacts, relationships, outreach]
    created: "2026-02-15"

  - id: "FILE-348"
    path: "signals/outreach-log.yaml"
    type: data
    thread_id: "THR-039"
    title: "Outreach Log — Action Tracking"
    summary: "Chronological log of outreach actions by entry_id, channel (linkedin/email), date, and status (5KB, last modified 2026-04-04)"
    tags: [outreach, actions, tracking, crm]
    created: "2026-02-15"

  - id: "FILE-349"
    path: "signals/network.yaml"
    type: data
    thread_id: "THR-039"
    title: "Network Graph — Node/Edge Topology"
    summary: "Network graph with nodes (name, org, role, degree, channel, tags) and edges for path-finding; used by network_graph.py for BFS/DFS and Granovetter weak-ties scoring (51KB)"
    tags: [network, graph, bfs, weak-ties, pathfinding]
    created: "2026-02-20"

  - id: "FILE-350"
    path: "signals/network-map.yaml"
    type: data
    thread_id: "THR-039"
    title: "Network Map — Visualization Data"
    summary: "Lightweight network map data for visualization (710 bytes)"
    tags: [network, visualization, map]
    created: "2026-03-20"

  - id: "FILE-351"
    path: "signals/conversion-log.yaml"
    type: data
    thread_id: "THR-040"
    title: "Conversion Log — Pipeline Funnel Tracking"
    summary: "Tracks entries through pipeline stages with submission dates, tracks, identity positions, blocks used, and channel data (33KB, last modified 2026-04-14)"
    tags: [conversion, funnel, analytics, tracking]
    created: "2026-02-24"

  - id: "FILE-352"
    path: "signals/hypotheses.yaml"
    type: data
    thread_id: "THR-040"
    title: "Hypotheses — Outcome Predictions"
    summary: "Hypothesis tracking with entry_id, category, predicted outcome, resolution date, and evidence; enables closed-loop learning (8KB)"
    tags: [hypotheses, predictions, learning, outcomes]
    created: "2026-03-02"

  - id: "FILE-353"
    path: "signals/signal-actions.yaml"
    type: data
    thread_id: "THR-040"
    title: "Signal Actions — Audit Trail"
    summary: "Signal-to-action audit trail logging all automated and manual signal processing decisions (540KB, largest signal file)"
    tags: [audit, signals, automation, trail]
    created: "2026-02-15"

  - id: "FILE-354"
    path: "signals/agent-actions.yaml"
    type: data
    thread_id: "THR-040"
    title: "Agent Actions — Autonomous Run History"
    summary: "Agent execution history tracking autonomous pipeline agent decisions and actions (3KB)"
    tags: [agent, automation, history, decisions]
    created: "2026-02-15"

  - id: "FILE-355"
    path: "signals/process-telemetry.yaml"
    type: data
    thread_id: "THR-040"
    title: "Process Telemetry — SPEC-023 Compliance"
    summary: "Process telemetry for SPEC-023 governance compliance tracking (343 bytes)"
    tags: [telemetry, governance, spec-023, compliance]
    created: "2026-03-15"

  - id: "FILE-356"
    path: "signals/score-telemetry.yaml"
    type: data
    thread_id: "THR-040"
    title: "Score Telemetry — Scoring Analytics"
    summary: "Score calculation telemetry for analytics and calibration (26KB)"
    tags: [scoring, telemetry, analytics, calibration]
    created: "2026-03-01"

  - id: "FILE-357"
    path: "signals/notification-log.yaml"
    type: data
    thread_id: "THR-040"
    title: "Notification Log — Event Delivery"
    summary: "Notification delivery log for pipeline events (4KB)"
    tags: [notifications, events, delivery, logging]
    created: "2026-03-01"

  - id: "FILE-358"
    path: "signals/text-match-corpus.yaml"
    type: data
    thread_id: "THR-040"
    title: "Text Match Corpus — TF-IDF Reference Data"
    summary: "TF-IDF text matching corpus for overlap detection between cover letters and resumes (54KB)"
    tags: [text-match, tfidf, overlap, detection]
    created: "2026-03-01"

## 4.1: IRA Ratings (signals/ratings/)

  - id: "FILE-359"
    path: "signals/ratings/"
    type: data
    thread_id: "THR-041"
    title: "IRA Rating Files — Inter-Rater Agreement"
    summary: "Directory of 7 JSON rating files for multi-model inter-rater agreement analysis across 9 evaluation dimensions"
    tags: [ira, ratings, inter-rater, evaluation, consensus]
    created: "2026-03-14"

  - id: "FILE-360"
    path: "signals/ratings/consensus-2026-03-14.json"
    type: data
    thread_id: "THR-041"
    title: "Consensus Ratings — 2026-03-14"
    summary: "Consensus rating file aggregating multi-rater scores (3KB)"
    tags: [consensus, ira, aggregated, ratings]
    created: "2026-03-14"

  - id: "FILE-361"
    path: "signals/ratings/objective.json"
    type: data
    thread_id: "THR-041"
    title: "Objective Dimension Ratings"
    summary: "Objective dimension ratings for IRA analysis (2KB)"
    tags: [objective, dimensions, ira]
    created: "2026-03-14"

  - id: "FILE-362"
    path: "signals/ratings/qa-lead.json"
    type: data
    thread_id: "THR-041"
    title: "QA Lead Persona Ratings"
    summary: "QA lead persona evaluation ratings (6KB)"
    tags: [qa-lead, persona, ratings]
    created: "2026-03-14"

  - id: "FILE-363"
    path: "signals/ratings/senior-engineer.json"
    type: data
    thread_id: "THR-041"
    title: "Senior Engineer Persona Ratings"
    summary: "Senior engineer persona evaluation ratings (5KB)"
    tags: [senior-engineer, persona, ratings]
    created: "2026-03-14"

  - id: "FILE-364"
    path: "signals/ratings/systems-architect.json"
    type: data
    thread_id: "THR-041"
    title: "Systems Architect Persona Ratings"
    summary: "Systems architect persona evaluation ratings (6KB)"
    tags: [systems-architect, persona, ratings]
    created: "2026-03-14"

  - id: "FILE-365"
    path: "signals/ratings/session-2026-03-25.json"
    type: data
    thread_id: "THR-041"
    title: "Session Ratings — 2026-03-25"
    summary: "Session-specific rating snapshot (600 bytes)"
    tags: [session, snapshot, ratings]
    created: "2026-03-25"

## 4.2: Daily Health Reports (signals/daily-health/)

  - id: "FILE-366"
    path: "signals/daily-health/"
    type: data
    thread_id: "THR-042"
    title: "Daily Health Reports — Pipeline Monitoring"
    summary: "Directory of 7 daily health report markdown files (Mar 16-22, 2026), ranging 27KB-174KB each, generated by monitor_pipeline.py --strict"
    tags: [health, monitoring, daily, reports]
    created: "2026-03-16"

## 4.3: Daily Snapshots (signals/daily-snapshots/)

  - id: "FILE-367"
    path: "signals/daily-snapshots/"
    type: data
    thread_id: "THR-042"
    title: "Daily Snapshots — State Serialization"
    summary: "Directory of 4 JSON snapshot files (Mar 19, 20, 30, Apr 3) capturing pipeline state at point in time (~500 bytes each)"
    tags: [snapshots, state, serialization, daily]
    created: "2026-03-19"

## 4.4: Weekly Briefs (signals/weekly-brief/)

  - id: "FILE-368"
    path: "signals/weekly-brief/"
    type: data
    thread_id: "THR-042"
    title: "Weekly Briefs — Strategic Summary"
    summary: "Directory of 6 weekly brief markdown files (Mar 15 - Apr 12, 2026) plus latest.md, generated by weekly_brief.py --save"
    tags: [weekly, brief, strategy, summary]
    created: "2026-03-15"

# ============================================================
# SECTION 5: STRATEGY/ — Scoring & Strategy Config
# ============================================================
# Strategy files define scoring weights, identity positions, agent rules, market intelligence, and governance

  - id: "FILE-369"
    path: "strategy/scoring-rubric.yaml"
    type: config
    thread_id: "THR-043"
    title: "Scoring Rubric v3.0 — Three-Pillar Weight Model"
    summary: "Three-pillar scoring weights: jobs (network_proximity 0.22, deadline_feasibility 0.18), grants, and consulting; auto-qualify thresholds; refactored 2026-03-25 from 2-rubric to 3-rubric model"
    tags: [scoring, weights, three-pillar, rubric, v3]
    created: "2026-02-23"

  - id: "FILE-370"
    path: "strategy/identity-positions.md"
    type: narrative
    thread_id: "THR-043"
    title: "Identity Positions — Nine Canonical Framings"
    summary: "Nine framings of the same body of work: Systems Artist, Educator, Creative Technologist, Community Practitioner, Independent Engineer, Documentation Engineer, Governance Architect, Platform Orchestrator, Founder/Operator (13KB)"
    tags: [identity, positions, framing, nine, narrative]
    created: "2026-03-15"

  - id: "FILE-371"
    path: "strategy/agent-rules.yaml"
    type: config
    thread_id: "THR-043"
    title: "Agent Rules — Autonomous Decision Engine"
    summary: "Decision rules for pipeline agent including channel allocator, adaptive feedback, score unscored research, and auto-qualification thresholds (3KB)"
    tags: [agent, rules, automation, decisions]
    created: "2026-03-27"

  - id: "FILE-372"
    path: "strategy/market-intelligence-2026.json"
    type: data
    thread_id: "THR-043"
    title: "Market Intelligence 2026 — 336 Sources"
    summary: "Market conditions data: 51,330 layoffs YTD 2026, 3.2% above pre-pandemic tech employment, 117% AI job posting growth; 336 sources, next review 2026-06-01 (35KB)"
    tags: [market, intelligence, layoffs, benchmarks, 2026]
    created: "2026-03-01"

  - id: "FILE-373"
    path: "strategy/notifications.yaml"
    type: config
    thread_id: "THR-043"
    title: "Notifications — Event Routing Config"
    summary: "Event routing configuration for webhooks and email notifications (569 bytes)"
    tags: [notifications, webhooks, email, routing]
    created: "2026-03-05"

  - id: "FILE-374"
    path: "strategy/system-grading-rubric.yaml"
    type: config
    thread_id: "THR-043"
    title: "System Grading Rubric — 9-Dimension Diagnostic"
    summary: "Nine-dimension diagnostic rubric for system grading used by diagnose.py (11KB)"
    tags: [grading, diagnostic, nine-dimension, rubric]
    created: "2026-03-14"

  - id: "FILE-375"
    path: "strategy/rater-personas.yaml"
    type: config
    thread_id: "THR-043"
    title: "Rater Personas — IRA Evaluation Profiles"
    summary: "Inter-rater agreement rater persona definitions for multi-model evaluation (2KB)"
    tags: [rater, personas, ira, evaluation]
    created: "2026-03-14"

  - id: "FILE-376"
    path: "strategy/module-verification-overrides.yaml"
    type: config
    thread_id: "THR-043"
    title: "Module Verification Overrides — CI Exceptions"
    summary: "Verification matrix override exceptions for module-to-test coverage (762 bytes)"
    tags: [verification, overrides, ci, exceptions]
    created: "2026-03-20"

  - id: "FILE-377"
    path: "strategy/scoring-rubric.md"
    type: narrative
    thread_id: "THR-043"
    title: "Scoring Rubric Documentation — Detailed Rationale"
    summary: "Detailed markdown documentation of scoring rubric rationale and methodology (16KB)"
    tags: [scoring, documentation, rationale, methodology]
    created: "2026-03-01"

  - id: "FILE-378"
    path: "strategy/system-standards.yaml"
    type: config
    thread_id: "THR-043"
    title: "System Standards — Pipeline Quality Gates"
    summary: "System-wide quality standards and governance rules (8KB)"
    tags: [standards, quality, governance, gates]
    created: "2026-03-26"

  - id: "FILE-379"
    path: "strategy/funding-landscape-2026.md"
    type: narrative
    thread_id: "THR-044"
    title: "Funding Landscape 2026 — Non-Dilutive Opportunities"
    summary: "Comprehensive funding landscape research for 2026 grants, residencies, and fellowships (26KB)"
    tags: [funding, landscape, grants, research, 2026]
    created: "2026-03-01"

  - id: "FILE-380"
    path: "strategy/market-research-corpus.md"
    type: narrative
    thread_id: "THR-044"
    title: "Market Research Corpus — 336 Source Citations"
    summary: "Aggregated market research corpus with citations for all numeric parameters in market intelligence (89KB)"
    tags: [market, research, corpus, citations]
    created: "2026-03-01"

  - id: "FILE-381"
    path: "strategy/startup-profile.yaml"
    type: config
    thread_id: "THR-044"
    title: "Startup Profile — Target Configuration"
    summary: "Startup target profile configuration for consulting track scoring (2KB)"
    tags: [startup, profile, consulting, targets]
    created: "2026-03-02"

  - id: "FILE-382"
    path: "strategy/storefront-playbook.md"
    type: narrative
    thread_id: "THR-044"
    title: "Storefront Playbook — Cathedral-to-Storefront Guide"
    summary: "Playbook for converting cathedral-depth work into scannable storefront presentations (5KB)"
    tags: [storefront, playbook, cathedral, presentation]
    created: "2026-03-15"

# ============================================================
# SECTION 6: BLOCKS/ — Narrative Modules
# ============================================================
# Composable narrative building blocks with tiered depth system (60s / 2min / 5min / cathedral)

  - id: "FILE-383"
    path: "blocks/README.md"
    type: narrative
    thread_id: "THR-045"
    title: "Blocks Documentation — Composable Narrative System"
    summary: "Documentation for the atomic content unit system explaining tier structure (60s/2min/5min/cathedral), block types, and referencing conventions (6KB)"
    tags: [blocks, documentation, tiers, narrative, composition]
    created: "2026-03-13"

  - id: "FILE-384"
    path: "blocks/_index.yaml"
    type: config
    thread_id: "THR-045"
    title: "Block Index — Master Registry"
    summary: "Master index of all blocks with metadata, tags, and cross-references (91KB)"
    tags: [index, registry, blocks, metadata]
    created: "2026-03-02"

  - id: "FILE-385"
    path: "blocks/cathedral.md"
    type: narrative
    thread_id: "THR-045"
    title: "Cathedral Block — Deep Immersive Narrative"
    summary: "Cathedral-tier block for deep systemic work narrative (515 bytes)"
    tags: [cathedral, deep, narrative, tier]
    created: "2026-05-12"

  - id: "FILE-386"
    path: "blocks/cathedral.md.j2"
    type: narrative
    thread_id: "THR-045"
    title: "Cathedral Template — Jinja2 Generator"
    summary: "Jinja2 template for cathedral block generation (757 bytes)"
    tags: [cathedral, template, jinja2, generation]
    created: "2026-03-04"

## 6.1: Identity Blocks (4 tiers: 60s, 2min, 5min, cathedral)

  - id: "FILE-387"
    path: "blocks/identity/60s.md"
    type: narrative
    thread_id: "THR-045"
    title: "Identity 60s — Elevator Pitch Block"
    summary: "60-second identity framing for quick introductions and scannable applications"
    tags: [identity, 60s, elevator-pitch, brief]
    created: "2026-03-01"

  - id: "FILE-388"
    path: "blocks/identity/2min.md"
    type: narrative
    thread_id: "THR-045"
    title: "Identity 2min — Short Form Block"
    summary: "2-minute identity narrative for standard application contexts"
    tags: [identity, 2min, short-form, narrative]
    created: "2026-03-01"

  - id: "FILE-389"
    path: "blocks/identity/5min.md"
    type: narrative
    thread_id: "THR-045"
    title: "Identity 5min — Medium Form Block"
    summary: "5-minute identity narrative for detailed application contexts"
    tags: [identity, 5min, medium-form, narrative]
    created: "2026-03-01"

## 6.2: Methodology Blocks

  - id: "FILE-390"
    path: "blocks/methodology/ai-conductor.md"
    type: narrative
    thread_id: "THR-045"
    title: "AI Conductor Methodology — Orchestration Pattern"
    summary: "Methodology block describing AI conductor orchestration approach for multi-agent systems"
    tags: [methodology, ai, conductor, orchestration]
    created: "2026-03-01"

  - id: "FILE-391"
    path: "blocks/methodology/founder-sustainability.md"
    type: narrative
    thread_id: "THR-045"
    title: "Founder Sustainability — Operational Resilience"
    summary: "Methodology block on sustainable solo operation at institutional scale"
    tags: [methodology, founder, sustainability, solo]
    created: "2026-03-01"

  - id: "FILE-392"
    path: "blocks/methodology/governance-as-art.md"
    type: narrative
    thread_id: "THR-045"
    title: "Governance as Art — Systems Aesthetics"
    summary: "Methodology block framing governance systems as artistic practice"
    tags: [methodology, governance, art, systems]
    created: "2026-03-01"

  - id: "FILE-393"
    path: "blocks/methodology/process-as-product.md"
    type: narrative
    thread_id: "THR-045"
    title: "Process as Product — Meta-Creation Framework"
    summary: "Methodology block on treating creative process itself as the product"
    tags: [methodology, process, product, meta]
    created: "2026-03-01"

## 6.3: Project Blocks (92 project blocks)

  - id: "FILE-394"
    path: "blocks/projects/"
    type: data
    thread_id: "THR-045"
    title: "Project Blocks — 92 Narrative Modules"
    summary: "Directory of 92 project-specific narrative blocks covering ORGANVM ecosystem projects, tools, and creative works"
    tags: [projects, blocks, narrative, 92, ecosystem]
    created: "2026-03-01"

  - id: "FILE-395"
    path: "blocks/projects/application-pipeline.md"
    type: narrative
    thread_id: "THR-045"
    title: "Application Pipeline Project Block — Self-Reference"
    summary: "Project block describing the application pipeline system itself as a creative artifact"
    tags: [project, pipeline, self-reference, meta]
    created: "2026-03-01"

## 6.4: Evidence & Framings

  - id: "FILE-396"
    path: "blocks/evidence/"
    type: data
    thread_id: "THR-045"
    title: "Evidence Blocks — Supporting Documentation"
    summary: "Directory of evidence blocks providing verifiable support for identity and project claims"
    tags: [evidence, verification, support, claims]
    created: "2026-03-01"

  - id: "FILE-397"
    path: "blocks/framings/"
    type: data
    thread_id: "THR-045"
    title: "Framing Blocks — Audience-Specific Angles"
    summary: "Directory of 19 framing blocks for audience-specific narrative positioning"
    tags: [framings, audience, positioning, 19]
    created: "2026-03-01"

  - id: "FILE-398"
    path: "blocks/pitches/"
    type: data
    thread_id: "THR-045"
    title: "Pitch Blocks — Ready-to-Use Submissions"
    summary: "Directory of 7 pre-composed pitch blocks for rapid submission"
    tags: [pitches, ready-to-use, submission, 7]
    created: "2026-03-01"

# ============================================================
# SECTION 7: MATERIALS/ — Resumes, Profiles, Variants
# ============================================================
# Target-specific content: 9 base resumes, 45 tailored resumes, 1,363 profiles, A/B variants

## 7.1: Base Resumes (9 identity-position templates)

  - id: "FILE-399"
    path: "materials/resumes/base/"
    type: artifact
    thread_id: "THR-046"
    title: "Base Resume Templates — 9 Identity Positions"
    summary: "Nine base resume templates (HTML + PDF) corresponding to canonical identity positions: community-practitioner, creative-technologist, documentation-engineer, educator, founder-operator, governance-architect, independent-engineer, platform-orchestrator, systems-artist"
    tags: [resumes, base, templates, nine, identity]
    created: "2026-03-28"

  - id: "FILE-400"
    path: "materials/resumes/base/creative-technologist-resume.html"
    type: artifact
    thread_id: "THR-046"
    title: "Creative Technologist Resume — Base Template"
    summary: "HTML resume template for creative technologist identity position (11KB)"
    tags: [resume, creative-technologist, html, template]
    created: "2026-03-28"

  - id: "FILE-401"
    path: "materials/resumes/base/documentation-engineer-resume.html"
    type: artifact
    thread_id: "THR-046"
    title: "Documentation Engineer Resume — Base Template"
    summary: "HTML resume template for documentation engineer identity position (11KB)"
    tags: [resume, documentation-engineer, html, template]
    created: "2026-03-28"

  - id: "FILE-402"
    path: "materials/resumes/base/cover-letter-template.html"
    type: artifact
    thread_id: "THR-046"
    title: "Cover Letter Template — HTML Base"
    summary: "Generic cover letter HTML template for pipeline composition (2KB)"
    tags: [cover-letter, template, html, generic]
    created: "2026-03-27"

## 7.2: Tailored Resumes (batch-03/ — 45 targets)

  - id: "FILE-403"
    path: "materials/resumes/batch-03/"
    type: artifact
    thread_id: "THR-046"
    title: "Batch 03 Tailored Resumes — 45 Target-Specific Versions"
    summary: "Directory of 45 target-tailored resume subdirectories, each containing HTML and PDF resumes customized for specific applications"
    tags: [resumes, batch-03, tailored, 45, targets]
    created: "2026-03-31"

  - id: "FILE-404"
    path: "materials/resumes/batch-03/creative-capital-2027/"
    type: artifact
    thread_id: "THR-046"
    title: "Creative Capital 2027 — Tailored Resume"
    summary: "Tailored resume for Creative Capital 2027 open call"
    tags: [resume, tailored, creative-capital, grant]
    created: "2026-03-31"

  - id: "FILE-405"
    path: "materials/resumes/batch-03/cursor-software-engineer-enterprise-platform/"
    type: artifact
    thread_id: "THR-046"
    title: "Cursor Enterprise Platform — Tailored Resume"
    summary: "Tailored resume for Cursor Software Engineer, Enterprise Platform role"
    tags: [resume, tailored, cursor, enterprise]
    created: "2026-03-31"

## 7.3: Variants (A/B tracked)

  - id: "FILE-406"
    path: "materials/variants/"
    type: artifact
    thread_id: "THR-047"
    title: "Content Variants — A/B Tracked Versions"
    summary: "Directory of A/B tracked content variants including cover letters, project descriptions, project pitches, statements, and README documentation"
    tags: [variants, ab-testing, content, tracked]
    created: "2026-03-01"

  - id: "FILE-407"
    path: "materials/variants/cover-letters/"
    type: artifact
    thread_id: "THR-047"
    title: "Cover Letter Variants — Template Library"
    summary: "Directory of cover letter variants for different tracks and identity positions"
    tags: [cover-letters, variants, templates, tracks]
    created: "2026-03-01"

  - id: "FILE-408"
    path: "materials/variants/project-descriptions/"
    type: artifact
    thread_id: "THR-047"
    title: "Project Description Variants — Multi-Length"
    summary: "Directory of project description variants at different lengths"
    tags: [project-descriptions, variants, multi-length]
    created: "2026-03-01"

  - id: "FILE-409"
    path: "materials/variants/statements/"
    type: artifact
    thread_id: "THR-047"
    title: "Statement Variants — Artist/Personal Statements"
    summary: "Directory of artist and personal statement variants"
    tags: [statements, variants, artist, personal]
    created: "2026-03-01"

## 7.4: Target Profiles (1,363 JSON files)

  - id: "FILE-410"
    path: "materials/targets/profiles/"
    type: data
    thread_id: "THR-048"
    title: "Target Profiles — 1,363 Pre-Written Content JSONs"
    summary: "Directory of 1,363 target-specific JSON profile files containing pre-written artist statements, bios, work samples at multiple lengths for rapid composition"
    tags: [profiles, targets, json, 1363, pre-written]
    created: "2026-02-15"

  - id: "FILE-411"
    path: "materials/targets/profiles/ai-consulting.json"
    type: data
    thread_id: "THR-048"
    title: "AI Consulting Profile — Target JSON"
    summary: "Target-specific profile for AI consulting track applications"
    tags: [profile, ai, consulting, target]
    created: "2026-02-15"

## 7.5: Target Directories (grants, jobs, residencies)

  - id: "FILE-412"
    path: "materials/targets/grants/"
    type: data
    thread_id: "THR-048"
    title: "Grant Targets — Funding Research"
    summary: "Grant target research including funding-research-exhaustive.md and track-grants-overview.md"
    tags: [grants, targets, research, funding]
    created: "2026-03-01"

  - id: "FILE-413"
    path: "materials/targets/jobs/"
    type: data
    thread_id: "THR-048"
    title: "Job Targets — Role Research"
    summary: "Job target research including ai-engineering-research.md and ai-engineering-role-research.md"
    tags: [jobs, targets, research, roles]
    created: "2026-03-01"

  - id: "FILE-414"
    path: "materials/targets/residencies/"
    type: data
    thread_id: "THR-048"
    title: "Residency Targets — Overview"
    summary: "Residency target research with track-residencies-overview.md"
    tags: [residencies, targets, research, overview]
    created: "2026-03-01"

# ============================================================
# SECTION 8: APPLICATIONS/ — Generated Submission Bundles
# ============================================================
# Dated submission bundles generated by apply.py: YYYY-MM-DD/<org>--<role>/
# 12 date directories, 37 entry bundles, 59 PDF artifacts total

  - id: "FILE-415"
    path: "applications/"
    type: artifact
    thread_id: "THR-049"
    title: "Application Bundles — Dated Submission Directory"
    summary: "Root directory of 12 dated submission bundles (Mar 13 - Apr 22, 2026) containing 37 individual application packages with cover letters, resumes, entry YAML, and portal answers"
    tags: [applications, bundles, dated, submissions, artifacts]
    created: "2026-03-13"

  - id: "FILE-416"
    path: "applications/2026-03-13/anduril--lead-technical-writer-intelligence-systems/"
    type: artifact
    thread_id: "THR-049"
    title: "Anduril Lead Technical Writer — First Application Bundle"
    summary: "First application bundle: cover letter (MD), resume (HTML+PDF), entry YAML — intelligence systems technical writing role"
    tags: [application, bundle, anduril, technical-writer, first]
    created: "2026-03-13"

  - id: "FILE-417"
    path: "applications/2026-03-17/"
    type: artifact
    thread_id: "THR-049"
    title: "March 17 Batch — 7 Application Bundles"
    summary: "Batch of 7 applications: Doppler, Harvey AI, LangChain, Notion, OpenAI, Stripe, plus outreach plan strategy documents"
    tags: [application, batch, march-17, seven, multi-org]
    created: "2026-03-17"

  - id: "FILE-418"
    path: "applications/2026-03-17/doppler--staff-full-stack-software-engineer/"
    type: artifact
    thread_id: "THR-049"
    title: "Doppler Staff Full-Stack — Complete Bundle"
    summary: "Complete application bundle: cover letter, resume (HTML+PDF), entry YAML, portal answers — secrets management platform"
    tags: [application, doppler, fullstack, complete, bundle]
    created: "2026-03-17"

  - id: "FILE-419"
    path: "applications/2026-03-17/outreach-plan.md"
    type: narrative
    thread_id: "THR-049"
    title: "Outreach Plan — Submission Strategy"
    summary: "Strategic outreach plan document for March 17 submission batch"
    tags: [outreach, plan, strategy, submission]
    created: "2026-03-17"

  - id: "FILE-420"
    path: "applications/2026-03-17/outreach-plan-strategy.md"
    type: narrative
    thread_id: "THR-049"
    title: "Outreach Plan Strategy — Detailed Approach"
    summary: "Detailed outreach strategy document with contact research and messaging approach"
    tags: [outreach, strategy, detailed, contacts]
    created: "2026-03-17"

  - id: "FILE-421"
    path: "applications/2026-03-25/"
    type: artifact
    thread_id: "THR-049"
    title: "March 25 Batch — Mid-Month Submissions"
    summary: "Mid-March application submission batch directory"
    tags: [application, batch, march-25, submissions]
    created: "2026-03-25"

  - id: "FILE-422"
    path: "applications/2026-03-31/"
    type: artifact
    thread_id: "THR-049"
    title: "March 31 Batch — Month-End Submissions"
    summary: "End-of-March application submission batch directory"
    tags: [application, batch, march-31, month-end]
    created: "2026-03-31"

  - id: "FILE-423"
    path: "applications/2026-04-22/"
    type: artifact
    thread_id: "THR-049"
    title: "April 22 Batch — Latest Submissions"
    summary: "Most recent application submission batch directory"
    tags: [application, batch, april-22, latest]
    created: "2026-04-22"

  - id: "FILE-424"
    path: "applications/interview-prep/"
    type: artifact
    thread_id: "THR-049"
    title: "Interview Prep — Preparation Materials"
    summary: "Directory of interview preparation materials for advanced-stage applications"
    tags: [interview, prep, materials, advanced]
    created: "2026-03-20"
