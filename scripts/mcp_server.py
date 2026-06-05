#!/usr/bin/env python3
"""MCP Server for the application pipeline.

Exposes core functions (score, advance, draft, validate) as MCP tools
using the clean API layer. No sys.argv manipulation or stdout redirection.

Enables agentic execution of the pipeline state machine without tight
coupling to script internals.
"""

import dataclasses
import json

from mcp.server.fastmcp import FastMCP

try:  # Prefer package-style imports when available.
    from .pipeline_api import (
        advance_entry,
        compose_entry,
        draft_entry,
        enrich_entry,
        followup_data,
        hygiene_check,
        load_precedent_registry,
        score_entry,
        standup_data,
        submit_entry,
        validate_entry,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from pipeline_api import (
        advance_entry,
        compose_entry,
        draft_entry,
        enrich_entry,
        followup_data,
        hygiene_check,
        load_precedent_registry,
        score_entry,
        standup_data,
        submit_entry,
        validate_entry,
    )

# Initialize FastMCP server
mcp = FastMCP("application-pipeline")


@mcp.tool()
def pipeline_score(
    entry_id: str | None = None,
    auto_qualify: bool = False,
    all_entries: bool = False,
) -> str:
    """Score a single entry or auto-qualify batch.
    
    Args:
        entry_id: Entry ID to score
        auto_qualify: If true, batch-advance research entries >= 7.0
        
    Returns:
        JSON result with status, entry_id, scores, and optional error
    """
    result = score_entry(
        entry_id=entry_id,
        auto_qualify=auto_qualify,
        all_entries=all_entries,
        dry_run=True,
    )
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "old_score": result.old_score,
        "new_score": result.new_score,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_advance(target_id: str, to_status: str | None = None) -> str:
    """Advance an entry to the next status in the pipeline.
    
    Args:
        target_id: Entry ID to advance
        to_status: Target status (optional)
        
    Returns:
        JSON result with status transition and optional error
    """
    result = advance_entry(entry_id=target_id, to_status=to_status, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "old_status": result.old_status,
        "new_status": result.new_status,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_draft(target_id: str) -> str:
    """Draft application materials from profile content.
    
    Args:
        target_id: Entry ID to draft
        
    Returns:
        JSON result with drafted content and optional file path
    """
    result = draft_entry(entry_id=target_id, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "content": result.content[:500] if result.content else None,  # First 500 chars
        "file_path": result.file_path,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_compose(target_id: str) -> str:
    """Compose submission from blocks.
    
    Args:
        target_id: Entry ID to compose
        
    Returns:
        JSON result with composed content and metadata
    """
    result = compose_entry(entry_id=target_id, dry_run=True)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "content": result.content[:500] if result.content else None,  # First 500 chars
        "word_count": result.word_count,
        "block_sources": result.block_sources,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_validate(target_id: str = None) -> str:
    """Validate pipeline YAML or specific entry.
    
    Args:
        target_id: Entry ID to validate (optional; validates all if not given)
        
    Returns:
        JSON result with validation status, errors, and warnings
    """
    result = validate_entry(entry_id=target_id)
    
    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "message": result.message,
    }, default=str)

@mcp.tool()
def list_precedents(domain: str | None = None) -> str:
    """List the precedent processes and domain implementations the product reuses.

    Serves the domain-surfaces registry that names the product's precedent
    processes (application_genesis, evaluative_authority, standards), the four
    boundary conditions a domain must meet, and each domain's instances.

    Args:
        domain: Narrow to one domain's instances (academic, market, engineering).
            Omit to return all domains.

    Returns:
        JSON with version, precedents, boundary_conditions, and domains
    """
    result = load_precedent_registry(domain=domain)

    return json.dumps({
        "status": result.status.value,
        "version": result.version,
        "description": result.description,
        "precedents": result.precedents,
        "boundary_conditions": result.boundary_conditions,
        "domains": result.domains,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_funnel() -> str:
    """Get conversion funnel analytics as JSON.

    Returns:
        JSON with portal, position, and track conversion stats
    """
    try:
        from conversion_dashboard import generate_dashboard_data
        from pipeline_lib import ALL_PIPELINE_DIRS, load_entries
        entries = load_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)
        data = generate_dashboard_data(entries)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_snapshot() -> str:
    """Capture current pipeline snapshot with counts, scores, and violations.

    Returns:
        JSON snapshot of current pipeline state
    """
    try:
        from snapshot import capture_snapshot
        data = capture_snapshot()
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_triage(min_score: float = 9.0, dry_run: bool = True) -> str:
    """Triage staged entries below threshold and org-cap violations.

    Args:
        min_score: Minimum score for staged entries (default: 9.0)
        dry_run: If true, preview only (default: true)

    Returns:
        JSON with staged_demotions, org_cap_deferrals, and summary
    """
    try:
        from pipeline_lib import load_entries
        from triage import generate_triage_data
        entries = load_entries()
        data = generate_triage_data(entries, min_score=min_score, dry_run=dry_run)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_crm_dashboard() -> str:
    """Get CRM dashboard data: contacts, orgs, overdue actions.

    Returns:
        JSON with contact stats, org coverage, and overdue items
    """
    try:
        from crm import generate_crm_data, load_contacts
        contacts = load_contacts()
        data = generate_crm_data(contacts)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_campaign(days: int = 14) -> str:
    """Get deadline-aware campaign data with urgency tiers.

    Args:
        days: Look-ahead window in days (default: 14)

    Returns:
        JSON with urgency tiers and entry details
    """
    try:
        from campaign import generate_campaign_data
        from pipeline_lib import load_entries
        entries = load_entries(include_filepath=True)
        data = generate_campaign_data(entries, days)
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_followup(target_id: str | None = None) -> str:
    """Get due follow-up actions for submitted entries.

    Args:
        target_id: Entry ID to check (optional; checks all if not given)

    Returns:
        JSON with due_actions list and summary
    """
    result = followup_data(entry_id=target_id)

    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "due_actions": result.due_actions,
        "total_entries": result.total_entries,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_hygiene(target_id: str | None = None) -> str:
    """Run hygiene gate checks on pipeline entries.

    Args:
        target_id: Entry ID to check (optional; checks all if not given)

    Returns:
        JSON with gate_issues, stale_entries, and total_issues count
    """
    result = hygiene_check(entry_id=target_id)

    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "gate_issues": result.gate_issues[:20] if result.gate_issues else [],
        "stale_entries": len(result.stale_entries) if result.stale_entries else 0,
        "total_issues": result.total_issues,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_enrich(target_id: str | None = None, all_entries: bool = False) -> str:
    """Analyze enrichment gaps for pipeline entries.

    Args:
        target_id: Entry ID to analyze (optional)
        all_entries: If true, analyze all entries

    Returns:
        JSON with gaps list and summary
    """
    result = enrich_entry(entry_id=target_id, all_entries=all_entries)

    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "gaps": result.gaps,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_standup(hours: float = 3.0, section: str | None = None) -> str:
    """Capture daily standup dashboard output.

    Args:
        hours: Available hours for today's session (default: 3.0)
        section: Run a single section only (optional)

    Returns:
        JSON with captured standup text output
    """
    result = standup_data(hours=hours, section=section)

    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "output": result.output[:2000] if result.output else None,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_submit(target_id: str) -> str:
    """Generate submission checklist for an entry.

    Args:
        target_id: Entry ID to generate checklist for

    Returns:
        JSON with checklist text and any issues found
    """
    result = submit_entry(entry_id=target_id, dry_run=True)

    return json.dumps({
        "status": result.status.value,
        "entry_id": result.entry_id,
        "checklist": result.checklist[:1500] if result.checklist else None,
        "issues": result.issues,
        "message": result.message,
        "error": result.error,
    }, default=str)


@mcp.tool()
def pipeline_org_intelligence(org_name: str | None = None) -> str:
    """Get organization intelligence rankings and details.

    Args:
        org_name: Organization name (optional; shows all rankings if not given)

    Returns:
        JSON with org rankings or single org detail
    """
    try:
        from org_intelligence import _load_contacts, rank_orgs
        from pipeline_lib import ALL_PIPELINE_DIRS, load_entries

        entries = load_entries(dirs=ALL_PIPELINE_DIRS, include_filepath=True)
        contacts = _load_contacts()
        ranked = rank_orgs(entries, contacts)

        if org_name:
            matched = [s for s in ranked if s.get("organization", "").lower() == org_name.lower()]
            if not matched:
                return json.dumps({"status": "error", "error": f"org '{org_name}' not found"})
            return json.dumps({"status": "success", "data": matched[0]}, default=str)

        return json.dumps({
            "status": "success",
            "data": ranked[:15],
            "total_orgs": len(ranked),
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_calibrate(dry_run: bool = True) -> str:
    """Calibrate scoring thresholds from external validation data.

    Reads BLS salary data, skill demand, and org signals from the
    validation cache and proposes concrete threshold updates to
    scoring-rubric.yaml and market-intelligence mode thresholds.

    Args:
        dry_run: If true, preview changes without writing (default: true)

    Returns:
        JSON with proposed calibrations and evidence
    """
    try:
        from external_validator import calibrate_thresholds
        result = calibrate_thresholds(dry_run=dry_run)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_audit(
    claims: bool = False,
    wiring: bool = False,
    logic: bool = False,
    external: bool = False,
) -> str:
    """System integrity audit: claims provenance, wiring, logic, external validation.

    Args:
        claims: Run claims provenance audit only
        wiring: Run wiring integrity audit only
        logic: Run logical consistency audit only
        external: Run external validation audit only

    Returns:
        JSON with audit results and summary
    """
    try:
        from audit_system import audit_claims, audit_external, audit_logic, audit_wiring, run_full_audit

        if external:
            result = audit_external()
            return json.dumps(result, default=str)

        run_all = not (claims or wiring or logic)
        if run_all:
            result = run_full_audit()
        else:
            result = {}
            if claims:
                result["claims"] = audit_claims()
            if wiring:
                result["wiring"] = audit_wiring()
            if logic:
                result["logic"] = audit_logic()

        # Trim claims list for JSON payload size
        if "claims" in result and "claims" in result["claims"]:
            unsourced = [c for c in result["claims"]["claims"] if c["status"] == "unsourced"]
            result["claims"]["claims"] = unsourced[:50]

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_standards(
    level: int | None = None,
    run_all: bool = False,
) -> str:
    """Run the Standards Board hierarchical validation audit.

    Args:
        level: Run a single level (1-5). None = full audit.
        run_all: If True, run all levels even if lower levels fail.

    Returns:
        JSON report with level reports, gate results, and pass/fail.
    """
    try:
        from standards import BoardReport, StandardsBoard
    except ImportError:
        from scripts.standards import BoardReport, StandardsBoard

    board = StandardsBoard()
    if level:
        lr = board.check_level(level)
        br = BoardReport(level_reports=[lr])
    else:
        br = board.full_audit(gated=not run_all)

    return json.dumps(br.to_dict(), indent=2)


@mcp.tool()
def pipeline_phase_analytics() -> str:
    """Compare Phase 1 (volume) vs Phase 2 (precision) application strategies.

    Returns:
        JSON with phase comparison data, velocity metrics, and conversion rates
    """
    try:
        from .phase_analytics import compute_phase_comparison
    except ImportError:
        from phase_analytics import compute_phase_comparison

    comparison = compute_phase_comparison()
    return json.dumps(comparison, indent=2)


@mcp.tool()
def pipeline_rate(
    rater_id: str | None = None,
    dry_run: bool = True,
    compute_ira: bool = False,
) -> str:
    """Run multi-model IRA rating session.

    Args:
        rater_id: Single rater to run (optional; runs all if not given)
        dry_run: If true, show prompts without calling APIs
        compute_ira: If true, compute IRA after rating

    Returns:
        JSON with status and list of completed raters
    """
    try:
        from generate_ratings import generate_ratings

        result = generate_ratings(
            dry_run=dry_run,
            single_rater=rater_id,
            compute_ira=compute_ira,
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_mode(
    set_mode: str | None = None,
    dry_run: bool = True,
) -> str:
    """Show or switch pipeline mode (precision/volume/hybrid).

    Args:
        set_mode: Mode to switch to (optional; shows current if not given)
        dry_run: If true, preview mode switch without applying

    Returns:
        JSON with current mode, thresholds, and changes
    """
    try:
        from pipeline_mode import compare_modes
        from pipeline_mode import set_mode as do_set_mode

        if set_mode:
            result = do_set_mode(set_mode, dry_run=dry_run)
        else:
            result = compare_modes()

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_outreach(target_id: str, template_type: str | None = None) -> str:
    """Generate outreach templates for a pipeline entry.

    Args:
        target_id: Entry ID to generate templates for
        template_type: connect, email, or followup (optional; all if not given)

    Returns:
        JSON with outreach templates
    """
    try:
        from outreach_templates import (
            _find_entry,
            generate_all_templates,
            generate_cold_email,
            generate_connect_note,
            generate_followup,
        )

        entry = _find_entry(target_id)
        if not entry:
            return json.dumps({"status": "error", "error": f"Entry not found: {target_id}"})

        if template_type == "connect":
            result = generate_connect_note(entry)
        elif template_type == "email":
            result = generate_cold_email(entry)
        elif template_type == "followup":
            result = generate_followup(entry)
        else:
            result = generate_all_templates(entry)

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_scan(sources: str = "all", max_entries: int = 100) -> str:
    """Scan all job sources for new postings (dry-run). Returns new entry IDs."""
    try:
        from scan_orchestrator import scan_all

        source_list = None if sources == "all" else sources.split(",")
        result = scan_all(dry_run=True, sources=source_list, max_entries=max_entries)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_match(target_id: str = "", top_n: int = 10) -> str:
    """Score unscored entries and rank top matches (dry-run)."""
    try:
        from match_engine import match_and_rank

        entry_ids = [target_id] if target_id else None
        result = match_and_rank(entry_ids=entry_ids, top_n=top_n, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_build(target_id: str = "") -> str:
    """Generate application materials for qualified entries (dry-run)."""
    try:
        from material_builder import build_materials

        entry_ids = [target_id] if target_id else None
        result = build_materials(entry_ids=entry_ids, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_apply(target_id: str = "") -> str:
    """Check readiness and submit staged entries via ATS portals (dry-run)."""
    try:
        from apply_engine import apply_ready_entries

        entry_ids = [target_id] if target_id else None
        result = apply_ready_entries(entry_ids=entry_ids, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_outreach_prep(target_id: str = "") -> str:
    """Generate outreach templates and set follow-up dates (dry-run)."""
    try:
        from outreach_engine import prepare_outreach

        entry_ids = [target_id] if target_id else None
        result = prepare_outreach(entry_ids=entry_ids, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_preflight() -> str:
    """Check system readiness for autonomous pipeline operation."""
    try:
        from daily_pipeline_orchestrator import preflight_check

        result = preflight_check()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


if __name__ == "__main__":
    # Start the MCP server using stdio transport
    mcp.run()
