#!/usr/bin/env python3
"""System integrity audit — claims provenance, wiring integrity, logical consistency.

Verifies that:
1. Statistical claims in the codebase trace to named sources
2. Rubric-to-code cross-references are consistently wired
3. Hardcoded values are logically sound (ranges, ordering, sums)

Usage:
    python scripts/audit_system.py                    # Full audit
    python scripts/audit_system.py --claims           # Claims provenance only
    python scripts/audit_system.py --wiring           # Wiring integrity only
    python scripts/audit_system.py --logic            # Logical consistency only
    python scripts/audit_system.py --json             # Machine-readable output
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import DIMENSION_ORDER, REPO_ROOT, VALID_DIMENSIONS

SCRIPTS_DIR = REPO_ROOT / "scripts"
STRATEGY_DIR = REPO_ROOT / "strategy"
RUBRIC_PATH = STRATEGY_DIR / "scoring-rubric.yaml"
SYSTEM_RUBRIC_PATH = STRATEGY_DIR / "system-grading-rubric.yaml"
MARKET_JSON_PATH = STRATEGY_DIR / "market-intelligence-2026.json"


# ---------------------------------------------------------------------------
# Claim Provenance Audit
# ---------------------------------------------------------------------------

# Patterns that look like statistical claims
CLAIM_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*%"),         # percentages: 62%, 5.75%
    re.compile(r"(\d+(?:\.\d+)?)\s*x\b"),        # multipliers: 8x
    re.compile(r"\$\s*([\d,]+(?:\.\d+)?)"),       # dollar amounts: $20,352
]

# Source indicator patterns (nearby text suggesting attribution)
SOURCE_INDICATORS = [
    re.compile(r'(?:source|cited|reference|per|from|according to)\s*[:=]?\s*["\']?[\w]', re.I),
    re.compile(r'\b(Huntr|ResumeGenius|LinkedIn|Glassdoor|Apollo|Indeed|Wellfound|Resume Now|Zety)\b'),
    re.compile(r'https?://\S+'),
    re.compile(r'"source"\s*:'),
    re.compile(r'"note"\s*:'),
    re.compile(r'\([\w\s]+\d{4}[^)]*\)'),  # parenthetical citations like (Huntr 2025)
]

# Citation quality tiers (highest to lowest)
# academic: peer-reviewed journal, DOI, .edu domain
# government: BLS, Census, NSF, .gov domain
# industry: named industry report (Gartner, McKinsey, PitchBook, Carta)
# content_marketing: blog posts, SEO content (ResumeGenius, Zety, Resume Now)
# unsourced: no attribution found

ACADEMIC_INDICATORS = [
    re.compile(r'\bdoi\b[:/]', re.I),
    re.compile(r'\bjournal\s+of\b', re.I),
    re.compile(r'\barxiv\b', re.I),
    re.compile(r'https?://\S+\.edu\b'),
    re.compile(r'\bpeer[- ]reviewed\b', re.I),
    re.compile(r'\bet\s+al\.\b', re.I),
    re.compile(r'\bIEEE\b|\bACM\b|\bNBER\b'),
]

GOVERNMENT_INDICATORS = [
    re.compile(r'\bBLS\b|\bBureau of Labor Statistics\b', re.I),
    re.compile(r'\bCensus\b', re.I),
    re.compile(r'\bNSF\b|\bNational Science Foundation\b', re.I),
    re.compile(r'\bNEA\b|\bNational Endowment\b', re.I),
    re.compile(r'https?://\S+\.gov\b'),
    re.compile(r'\bFederal\s+Reserve\b', re.I),
    re.compile(r'\bSBIR\b|\bSTTR\b'),
]

INDUSTRY_INDICATORS = [
    re.compile(r'\b(Gartner|McKinsey|Deloitte|PwC|KPMG|Accenture)\b'),
    re.compile(r'\b(PitchBook|Carta|Crunchbase|CB Insights|Preqin)\b'),
    re.compile(r'\b(Forrester|IDC|Statista|LinkedIn Economic Graph)\b'),
    re.compile(r'\b(Stack Overflow|GitHub|JetBrains)\s+(Survey|Report|State of)\b', re.I),
]

CONTENT_MARKETING_INDICATORS = [
    re.compile(r'\b(ResumeGenius|Resume Now|Zety|TopResume|Jobscan)\b'),
    re.compile(r'\b(HiringHello|CandorCo|TheInterviewGuys|La Fosse Academy)\b'),
    re.compile(r'\b(Equip\.co|SpotSaaS|Index\.dev)\b'),
]


def _classify_citation_quality(text: str, claim_pos: int, window: int = 300) -> str:
    """Classify citation quality tier for a claim. Returns quality tier string."""
    start = max(0, claim_pos - window)
    end = min(len(text), claim_pos + window)
    context = text[start:end]

    # Check tiers from highest to lowest quality
    for pattern in ACADEMIC_INDICATORS:
        if pattern.search(context):
            return "academic"

    for pattern in GOVERNMENT_INDICATORS:
        if pattern.search(context):
            return "government"

    for pattern in INDUSTRY_INDICATORS:
        if pattern.search(context):
            return "industry"

    for pattern in CONTENT_MARKETING_INDICATORS:
        if pattern.search(context):
            return "content_marketing"

    return "unknown"


def _has_source_nearby(text: str, claim_pos: int, window: int = 300) -> str:
    """Check if source attribution exists near a claim. Returns status."""
    start = max(0, claim_pos - window)
    end = min(len(text), claim_pos + window)
    context = text[start:end]

    for pattern in SOURCE_INDICATORS:
        if pattern.search(context):
            # Check for URL specifically
            if re.search(r'https?://\S+', context):
                return "sourced"
            return "cited"
    return "unsourced"


def audit_claims() -> dict:
    """Scan scripts/ and strategy/ for statistical claims and check provenance."""
    results = {
        "claims": [],
        "summary": {"sourced": 0, "cited": 0, "unsourced": 0},
        "quality": {"academic": 0, "government": 0, "industry": 0, "content_marketing": 0, "unknown": 0},
    }

    scan_dirs = [
        (SCRIPTS_DIR, "*.py"),
        (STRATEGY_DIR, "*.json"),
        (STRATEGY_DIR, "*.yaml"),
        (STRATEGY_DIR, "*.md"),
    ]

    for scan_dir, glob_pattern in scan_dirs:
        if not scan_dir.exists():
            continue
        for filepath in sorted(scan_dir.glob(glob_pattern)):
            if filepath.name.startswith("_"):
                continue
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for pattern in CLAIM_PATTERNS:
                for match in pattern.finditer(text):
                    # Get line number and context
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(text)
                    line_num = text[:match.start()].count("\n") + 1
                    line_text = text[line_start:line_end].strip()

                    # Skip trivial matches (single-digit percentages in code logic, etc.)
                    value_str = match.group(1) if match.lastindex else match.group(0)
                    try:
                        float(value_str.replace(",", ""))
                    except ValueError:
                        continue

                    # Skip code-only patterns (loop indices, format specs, etc.)
                    if "range(" in line_text or "for " in line_text and "in " in line_text:
                        continue
                    if line_text.startswith("#") or line_text.startswith("//"):
                        pass  # comments are valid claim locations
                    if len(line_text) < 10:
                        continue

                    status = _has_source_nearby(text, match.start())
                    quality = _classify_citation_quality(text, match.start()) if status != "unsourced" else "unknown"
                    results["summary"][status] += 1
                    results["quality"][quality] += 1
                    results["claims"].append({
                        "file": str(filepath.relative_to(REPO_ROOT)),
                        "line": line_num,
                        "claim": match.group(0).strip(),
                        "context": line_text[:120],
                        "status": status,
                        "quality": quality,
                    })

    return results


# ---------------------------------------------------------------------------
# Wiring Integrity Audit
# ---------------------------------------------------------------------------

def audit_wiring() -> dict:
    """Verify cross-references between rubrics, code, and constants are consistent."""
    checks = []

    # 1. Scoring rubric weights match code defaults
    rubric = {}
    if RUBRIC_PATH.exists():
        with open(RUBRIC_PATH) as f:
            rubric = yaml.safe_load(f) or {}

    rubric_weights = rubric.get("weights", {})
    rubric_weights_job = rubric.get("weights_job", {})

    # Load code defaults from score.py (three-pillar: WEIGHTS falls back to the
    # grant pillar set, so the legacy "weights" key maps to _DEFAULT_WEIGHTS_GRANT)
    try:
        import score as _score_mod
        code_weights = _score_mod._DEFAULT_WEIGHTS_GRANT
        code_weights_job = _score_mod._DEFAULT_WEIGHTS_JOB
        checks.append(_check(
            "rubric_weights_match_code",
            "Scoring rubric weights match score.py defaults",
            rubric_weights == code_weights,
            f"YAML: {rubric_weights}, Code: {code_weights}" if rubric_weights != code_weights else "Match",
        ))
        checks.append(_check(
            "rubric_weights_job_match_code",
            "Scoring rubric job weights match score.py defaults",
            rubric_weights_job == code_weights_job,
            f"YAML: {rubric_weights_job}, Code: {code_weights_job}" if rubric_weights_job != code_weights_job else "Match",
        ))
    except Exception as e:
        checks.append(_check("rubric_weights_match_code", "Scoring rubric weights match score.py defaults", False, f"Import error: {e}"))

    # 2. Scoring dimensions consistent across modules. Three-pillar model: each
    #    weight set uses a pillar-specific SUBSET of VALID_DIMENSIONS, so we check
    #    subset relationships rather than equality.
    rubric_dims = set(rubric_weights.keys())
    for _k in ("weights_job", "weights_grant", "weights_consulting"):
        rubric_dims |= set(rubric.get(_k, {}).keys())
    pipeline_dims = set(DIMENSION_ORDER)
    validate_dims = set(VALID_DIMENSIONS)

    checks.append(_check(
        "dimensions_rubric_eq_pipeline",
        "pipeline_lib.DIMENSION_ORDER (9 core) is a subset of VALID_DIMENSIONS",
        pipeline_dims <= validate_dims,
        f"Core dims not valid: {sorted(pipeline_dims - validate_dims)}" if not pipeline_dims <= validate_dims else "Subset",
    ))
    checks.append(_check(
        "dimensions_rubric_eq_validate",
        "All rubric weight-set dimensions are valid (subset of VALID_DIMENSIONS)",
        rubric_dims <= validate_dims,
        f"Unknown rubric dims: {sorted(rubric_dims - validate_dims)}" if not rubric_dims <= validate_dims else "Subset",
    ))

    # 3. System grading rubric matches diagnose.py
    sys_rubric = {}
    if SYSTEM_RUBRIC_PATH.exists():
        with open(SYSTEM_RUBRIC_PATH) as f:
            sys_rubric = yaml.safe_load(f) or {}

    sys_dims = set(sys_rubric.get("dimensions", {}).keys())
    try:
        import diagnose as _diag
        diag_dims = set(_diag.OBJECTIVE_DIMENSIONS) | set(_diag.SUBJECTIVE_DIMENSIONS)
        checks.append(_check(
            "system_rubric_matches_diagnose",
            "System rubric dimensions == diagnose.py dimension lists",
            sys_dims == diag_dims,
            f"Rubric: {sorted(sys_dims)}, Diagnose: {sorted(diag_dims)}" if sys_dims != diag_dims else "Match",
        ))
    except Exception as e:
        checks.append(_check("system_rubric_matches_diagnose", "System rubric matches diagnose.py", False, f"Import error: {e}"))

    # 4. System rubric weights sum to 1.0
    sys_weights = {k: v.get("weight", 0) for k, v in sys_rubric.get("dimensions", {}).items()}
    sys_weight_sum = sum(sys_weights.values())
    checks.append(_check(
        "system_rubric_weights_sum",
        "System rubric dimension weights sum to 1.0",
        abs(sys_weight_sum - 1.0) < 0.001,
        f"Sum: {sys_weight_sum:.4f}",
    ))

    # 5. Thresholds match
    rubric_thresholds = rubric.get("thresholds", {})
    try:
        import score as _score_mod2
        checks.append(_check(
            "threshold_auto_qualify",
            "Rubric auto_qualify_min matches score.py AUTO_QUALIFY_MIN",
            rubric_thresholds.get("auto_qualify_min") == _score_mod2.AUTO_QUALIFY_MIN,
            f"Rubric: {rubric_thresholds.get('auto_qualify_min')}, Code: {_score_mod2.AUTO_QUALIFY_MIN}",
        ))
    except Exception:
        pass

    # 6. Market intelligence JSON completeness
    if MARKET_JSON_PATH.exists():
        with open(MARKET_JSON_PATH) as f:
            market = json.load(f)
        sections_without_source = []
        for key, val in market.items():
            if isinstance(val, dict):
                has_source = "source" in val or "note" in val or "_note" in val
                # Check nested dicts too
                if not has_source:
                    for sub_val in val.values():
                        if isinstance(sub_val, dict) and ("source" in sub_val or "note" in sub_val):
                            has_source = True
                            break
                if not has_source:
                    sections_without_source.append(key)
        checks.append(_check(
            "market_json_sourced",
            "All market-intelligence sections have source/note fields",
            len(sections_without_source) == 0,
            f"Missing: {sections_without_source}" if sections_without_source else "All sections sourced",
        ))

    # 7. HIGH_PRESTIGE score ranges
    try:
        import score_constants
        out_of_range = {k: v for k, v in score_constants.HIGH_PRESTIGE.items() if not (1 <= v <= 10)}
        checks.append(_check(
            "high_prestige_ranges",
            "All HIGH_PRESTIGE org scores in 1-10 range",
            len(out_of_range) == 0,
            f"Out of range: {out_of_range}" if out_of_range else f"All {len(score_constants.HIGH_PRESTIGE)} orgs valid",
        ))
    except Exception as e:
        checks.append(_check("high_prestige_ranges", "HIGH_PRESTIGE scores in range", False, str(e)))

    # 8. ROLE_FIT_TIERS score ranges
    try:
        import score_constants as _sc
        tier_issues = []
        for tier in _sc.ROLE_FIT_TIERS:
            for dim in ["mission_alignment", "evidence_match", "track_record_fit"]:
                val = tier.get(dim)
                if val is not None and not (1 <= val <= 10):
                    tier_issues.append(f"{tier['name']}.{dim}={val}")
        checks.append(_check(
            "role_fit_tier_ranges",
            "All ROLE_FIT_TIERS dimension scores in 1-10 range",
            len(tier_issues) == 0,
            f"Issues: {tier_issues}" if tier_issues else "All tiers valid",
        ))
    except Exception as e:
        checks.append(_check("role_fit_tier_ranges", "ROLE_FIT_TIERS scores in range", False, str(e)))

    # 9. IRA config sanity
    ira_config = sys_rubric.get("ira", {})
    checks.append(_check(
        "ira_min_raters",
        "IRA min_raters >= 2",
        ira_config.get("min_raters", 0) >= 2,
        f"min_raters: {ira_config.get('min_raters')}",
    ))

    passed = sum(1 for c in checks if c["passed"])
    return {"checks": checks, "summary": {"passed": passed, "total": len(checks)}}


def _check(check_id: str, description: str, passed: bool, detail: str = "") -> dict:
    return {"id": check_id, "description": description, "passed": passed, "detail": detail}


# ---------------------------------------------------------------------------
# Logical Consistency Audit
# ---------------------------------------------------------------------------

def audit_logic() -> dict:
    """Check for impossible, improbable, or illogical values."""
    checks = []

    # 1. Weight sums
    rubric = {}
    if RUBRIC_PATH.exists():
        with open(RUBRIC_PATH) as f:
            rubric = yaml.safe_load(f) or {}

    for key in ["weights", "weights_job"]:
        weights = rubric.get(key, {})
        if weights:
            wsum = sum(weights.values())
            checks.append(_check(
                f"weight_sum_{key}",
                f"{key} sum to 1.0",
                abs(wsum - 1.0) < 0.001,
                f"Sum: {wsum:.6f}",
            ))

    # 2. Threshold ordering
    thresholds = rubric.get("thresholds", {})
    t1 = thresholds.get("tier1_cutoff", 0)
    t2 = thresholds.get("tier2_cutoff", 0)
    t3 = thresholds.get("tier3_cutoff", 0)
    checks.append(_check(
        "threshold_ordering",
        "tier1_cutoff > tier2_cutoff > tier3_cutoff",
        t1 > t2 > t3 > 0,
        f"tier1={t1}, tier2={t2}, tier3={t3}",
    ))

    # 3. Score range sanity
    score_min = thresholds.get("score_range_min", 1)
    score_max = thresholds.get("score_range_max", 10)
    checks.append(_check(
        "score_range_valid",
        "Score range min < max and both positive",
        0 < score_min < score_max <= 100,
        f"min={score_min}, max={score_max}",
    ))

    # 4. Market intelligence logical checks
    if MARKET_JSON_PATH.exists():
        with open(MARKET_JSON_PATH) as f:
            market = json.load(f)

        # Channel multiplier sanity
        channels = market.get("channel_multipliers", {})
        bad_multipliers = []
        for ch, data in channels.items():
            if isinstance(data, dict):
                mult = data.get("response_rate_multiplier")
                if mult is not None and (mult < 0 or mult > 50):
                    bad_multipliers.append(f"{ch}={mult}")
        checks.append(_check(
            "channel_multiplier_sanity",
            "Channel multipliers in sane range (0-50x)",
            len(bad_multipliers) == 0,
            f"Bad: {bad_multipliers}" if bad_multipliers else f"All {len(channels)} channels valid",
        ))

        # Conversion rate sanity
        benchmarks = market.get("volume_benchmarks", {})
        bad_rates = []
        for key, val in benchmarks.items():
            if isinstance(val, (int, float)) and "rate" in key:
                if val < 0 or val > 1.0:
                    bad_rates.append(f"{key}={val}")
        checks.append(_check(
            "conversion_rate_sanity",
            "Conversion rates in 0.0-1.0 range",
            len(bad_rates) == 0,
            f"Bad: {bad_rates}" if bad_rates else "All rates valid",
        ))

        # Follow-up window ordering
        protocol = market.get("follow_up_protocol", {})
        connect = protocol.get("connect_window_days", [0, 0])
        dm1 = protocol.get("first_dm_days", [0, 0])
        dm2 = protocol.get("second_dm_days", [0, 0])
        if isinstance(connect, list) and isinstance(dm1, list) and isinstance(dm2, list):
            window_ok = (
                len(connect) == 2 and len(dm1) == 2 and len(dm2) == 2
                and connect[0] <= connect[1]
                and dm1[0] <= dm1[1]
                and dm2[0] <= dm2[1]
                and connect[1] <= dm1[0]
                and dm1[1] <= dm2[0]
            )
            checks.append(_check(
                "followup_window_ordering",
                "Follow-up protocol windows are sequential and non-overlapping",
                window_ok,
                f"connect={connect}, dm1={dm1}, dm2={dm2}",
            ))

        # Salary range sanity
        salaries = market.get("salary_benchmarks", {})
        salary_issues = []
        for role, data in salaries.items():
            if isinstance(data, dict):
                smin = data.get("min", 0)
                smax = data.get("max", 0)
                if smin > smax:
                    salary_issues.append(f"{role}: min({smin}) > max({smax})")
                if smax > 1_000_000:
                    salary_issues.append(f"{role}: max({smax}) > $1M")
        checks.append(_check(
            "salary_range_sanity",
            "Salary benchmarks have valid min/max ranges",
            len(salary_issues) == 0,
            f"Issues: {salary_issues}" if salary_issues else f"All {len(salaries)} roles valid",
        ))

    # 5. Benefits cliff sanity
    cliffs = rubric.get("benefits_cliffs", {})
    cliff_issues = []
    for name, val in cliffs.items():
        if not isinstance(val, (int, float)) or val <= 0 or val > 100_000:
            cliff_issues.append(f"{name}={val}")
    if cliffs:
        checks.append(_check(
            "benefits_cliff_sanity",
            "Benefits cliff thresholds positive and < $100k",
            len(cliff_issues) == 0,
            f"Issues: {cliff_issues}" if cliff_issues else f"All {len(cliffs)} cliffs valid",
        ))

    # 6. ROLE_FIT_TIERS ordering (tier-1 should score highest)
    try:
        import score_constants as _sc
        tier_scores = {}
        for tier in _sc.ROLE_FIT_TIERS:
            name = tier.get("name", "?")
            avg = sum(tier.get(d, 0) for d in ["mission_alignment", "evidence_match", "track_record_fit"]) / 3
            tier_scores[name] = round(avg, 1)

        # tier-1-strong should have highest avg, tier-4-poor lowest
        t1_avg = tier_scores.get("tier-1-strong", 0)
        t4_avg = tier_scores.get("tier-4-poor", 10)
        checks.append(_check(
            "role_tier_ordering",
            "tier-1-strong avg > tier-4-poor avg (role fit tiers logically ordered)",
            t1_avg > t4_avg,
            f"tier-1-strong avg={t1_avg}, tier-4-poor avg={t4_avg}",
        ))
    except Exception as e:
        checks.append(_check("role_tier_ordering", "Role tier ordering", False, str(e)))

    passed = sum(1 for c in checks if c["passed"])
    return {"checks": checks, "summary": {"passed": passed, "total": len(checks)}}


# ---------------------------------------------------------------------------
# Aggregate and output
# ---------------------------------------------------------------------------

def audit_external() -> dict:
    """Compare scoring inputs against externally fetched validation data.

    Requires a pre-populated validation cache at
    strategy/external-validation-cache.json (run external_validator.py first).
    """
    try:
        from external_validator import compare_against_scoring, load_cache
    except ImportError:
        return {"status": "error", "error": "external_validator.py not found"}

    cache = load_cache()
    if not cache:
        return {
            "status": "no_cache",
            "note": "Run: python scripts/external_validator.py --fetch-only",
        }

    return compare_against_scoring(cache)


def run_full_audit() -> dict:
    """Run all three audit classes and return combined results."""
    claims = audit_claims()
    wiring = audit_wiring()
    logic = audit_logic()

    total_wiring_passed = wiring["summary"]["passed"]
    total_wiring = wiring["summary"]["total"]
    total_logic_passed = logic["summary"]["passed"]
    total_logic = logic["summary"]["total"]

    return {
        "claims": claims,
        "wiring": wiring,
        "logic": logic,
        "summary": {
            "claims_sourced": claims["summary"]["sourced"],
            "claims_cited": claims["summary"]["cited"],
            "claims_unsourced": claims["summary"]["unsourced"],
            "claims_total": sum(claims["summary"].values()),
            "wiring_passed": total_wiring_passed,
            "wiring_total": total_wiring,
            "logic_passed": total_logic_passed,
            "logic_total": total_logic,
            "all_wiring_ok": total_wiring_passed == total_wiring,
            "all_logic_ok": total_logic_passed == total_logic,
        },
    }


def format_report(audit: dict) -> str:
    """Format a human-readable audit report."""
    lines = [
        "=" * 70,
        "  SYSTEM INTEGRITY AUDIT",
        "=" * 70,
        "",
    ]

    # Claims summary
    cs = audit["claims"]["summary"]
    cq = audit["claims"].get("quality", {})
    total_claims = cs["sourced"] + cs["cited"] + cs["unsourced"]
    lines.append(f"  CLAIMS PROVENANCE ({total_claims} claims scanned)")
    lines.append(f"    Sourced (URL):   {cs['sourced']}")
    lines.append(f"    Cited (name):    {cs['cited']}")
    lines.append(f"    Unsourced:       {cs['unsourced']}")
    if cq:
        lines.append("")
        lines.append("    Citation quality:")
        lines.append(f"      Academic:          {cq.get('academic', 0)}")
        lines.append(f"      Government:        {cq.get('government', 0)}")
        lines.append(f"      Industry report:   {cq.get('industry', 0)}")
        lines.append(f"      Content marketing: {cq.get('content_marketing', 0)}")
        lines.append(f"      Unclassified:      {cq.get('unknown', 0)}")
    if cs["unsourced"] > 0:
        lines.append("")
        lines.append("    Unsourced claims:")
        for claim in audit["claims"]["claims"]:
            if claim["status"] == "unsourced":
                lines.append(f"      {claim['file']}:{claim['line']} — {claim['claim']}")
                lines.append(f"        {claim['context'][:100]}")
    lines.append("")

    # Wiring checks
    ws = audit["wiring"]["summary"]
    lines.append(f"  WIRING INTEGRITY ({ws['passed']}/{ws['total']} passed)")
    for check in audit["wiring"]["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"    [{status}] {check['description']}")
        if not check["passed"] and check["detail"]:
            lines.append(f"           {check['detail'][:100]}")
    lines.append("")

    # Logic checks
    ls = audit["logic"]["summary"]
    lines.append(f"  LOGICAL CONSISTENCY ({ls['passed']}/{ls['total']} passed)")
    for check in audit["logic"]["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"    [{status}] {check['description']}")
        if not check["passed"] and check["detail"]:
            lines.append(f"           {check['detail'][:100]}")
    lines.append("")

    # Overall
    s = audit["summary"]
    all_ok = s["all_wiring_ok"] and s["all_logic_ok"]
    lines.append("  " + "-" * 50)
    lines.append(f"  OVERALL: {'CLEAN' if all_ok else 'ISSUES FOUND'}")
    lines.append(f"    Wiring: {s['wiring_passed']}/{s['wiring_total']}")
    lines.append(f"    Logic:  {s['logic_passed']}/{s['logic_total']}")
    lines.append(f"    Claims: {s['claims_sourced']} sourced, {s['claims_cited']} cited, {s['claims_unsourced']} unsourced (of {s['claims_total']})")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="System integrity audit — claims, wiring, logic",
    )
    parser.add_argument("--claims", action="store_true", help="Claims provenance only")
    parser.add_argument("--wiring", action="store_true", help="Wiring integrity only")
    parser.add_argument("--logic", action="store_true", help="Logical consistency only")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    # If no specific flag, run all
    run_all = not (args.claims or args.wiring or args.logic)

    if run_all:
        audit = run_full_audit()
    else:
        audit = {
            "claims": audit_claims() if args.claims else {"claims": [], "summary": {"sourced": 0, "cited": 0, "unsourced": 0}},
            "wiring": audit_wiring() if args.wiring else {"checks": [], "summary": {"passed": 0, "total": 0}},
            "logic": audit_logic() if args.logic else {"checks": [], "summary": {"passed": 0, "total": 0}},
        }
        cs = audit["claims"]["summary"]
        ws = audit["wiring"]["summary"]
        ls = audit["logic"]["summary"]
        audit["summary"] = {
            "claims_sourced": cs["sourced"],
            "claims_cited": cs["cited"],
            "claims_unsourced": cs["unsourced"],
            "claims_total": sum(cs.values()),
            "wiring_passed": ws["passed"],
            "wiring_total": ws["total"],
            "logic_passed": ls["passed"],
            "logic_total": ls["total"],
            "all_wiring_ok": ws["passed"] == ws["total"],
            "all_logic_ok": ls["passed"] == ls["total"],
        }

    if args.json:
        # Trim claims list for JSON readability (keep unsourced + first 20 others)
        if "claims" in audit and "claims" in audit["claims"]:
            unsourced = [c for c in audit["claims"]["claims"] if c["status"] == "unsourced"]
            others = [c for c in audit["claims"]["claims"] if c["status"] != "unsourced"][:20]
            audit["claims"]["claims"] = unsourced + others
        print(json.dumps(audit, indent=2, default=str))
    else:
        print(format_report(audit))


if __name__ == "__main__":
    main()
