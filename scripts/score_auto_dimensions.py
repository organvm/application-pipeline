"""Auto-derived dimension scoring utilities extracted from score.py."""

from __future__ import annotations

from pipeline_lib import (
    days_until,
    get_portal_scores,
    get_strategic_base,
    load_market_intelligence,
    parse_date,
)
from score_constants import HIGH_PRESTIGE


def score_deadline_feasibility(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score deadline feasibility from deadline data."""
    deadline = entry.get("deadline", {})
    if not isinstance(deadline, dict):
        result = 7
        if explain:
            return result, "deadline is not a dict -> default 7"
        return result

    dtype = deadline.get("type", "")
    date_str = deadline.get("date")

    if dtype in ("rolling", "tba") or not date_str:
        result = 9
        if explain:
            return result, f"type={dtype or 'no date'} -> 9 (no pressure)"
        return result

    deadline_date = parse_date(date_str)
    if not deadline_date:
        result = 7
        if explain:
            return result, f"unparseable date '{date_str}' -> default 7"
        return result

    days_left = days_until(deadline_date)

    if days_left < 0:
        result = 1
    elif days_left <= 1:
        result = 2
    elif days_left <= 3:
        result = 3
    elif days_left <= 5:
        result = 4
    elif days_left <= 7:
        result = 5
    elif days_left <= 14:
        result = 6
    elif days_left <= 30:
        result = 8
    else:
        result = 9

    submission = entry.get("submission", {})
    mat_bonus = False
    if isinstance(submission, dict):
        materials = submission.get("materials_attached") or []
        if materials and result < 9:
            result = min(9, result + 1)
            mat_bonus = True

    if explain:
        suffix = " + materials_ready (+1)" if mat_bonus else ""
        return result, f"{days_left}d left (date: {date_str}){suffix} -> {result}"
    return result


def score_financial_alignment(
    entry: dict,
    snap_limit: int,
    medicaid_limit: int,
    essential_plan_limit: int,
    explain: bool = False,
) -> int | tuple[int, str]:
    """Score financial alignment from amount and benefits cliffs."""
    amount = entry.get("amount", {})
    if not isinstance(amount, dict):
        result = 9
        if explain:
            return result, "amount is not a dict -> default 9"
        return result

    value = amount.get("value", 0)
    track = entry.get("track", "")

    if track == "job":
        if value == 0:
            result = 5
            reason = f"${value:,} (unknown) -> {result}"
        elif value > 150000:
            result = 9
            reason = f"${value:,} (>$150K) -> {result}"
        elif value > 100000:
            result = 8
            reason = f"${value:,} (>$100K) -> {result}"
        elif value > 50000:
            result = 7
            reason = f"${value:,} (>$50K) -> {result}"
        else:
            result = 6
            reason = f"${value:,} (low) -> {result}"
        if explain:
            return result, reason
        return result

    cliff_note = amount.get("benefits_cliff_note") or ""

    if value == 0:
        result = 7
        reason = "$0 (unknown/no amount — neutral) -> 7"
    elif "exceeds" in cliff_note.lower() or "nylag" in cliff_note.lower():
        result = 4
        reason = f"${value:,} cliff note '{cliff_note}' -> 4"
    elif "essential plan" in cliff_note.lower():
        result = 5
        reason = f"${value:,} cliff note '{cliff_note}' -> 5"
    elif value <= snap_limit:
        result = 9
        reason = f"${value:,} <= SNAP ${snap_limit:,} -> 9"
    elif value <= medicaid_limit:
        result = 8
        reason = f"${value:,} <= Medicaid ${medicaid_limit:,} -> 8"
    elif value <= essential_plan_limit:
        result = 6
        reason = f"${value:,} <= Essential Plan ${essential_plan_limit:,} -> 6"
    elif value <= 100000:
        result = 4
        reason = f"${value:,} > Essential Plan -> 4"
    else:
        result = 3
        reason = f"${value:,} > $100K -> 3 (severe cliff risk)"

    if explain:
        return result, reason
    return result


def score_portal_friction(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score portal friction from portal type."""
    target = entry.get("target", {})
    if not isinstance(target, dict):
        result = 6
        if explain:
            return result, "target is not a dict -> default 6"
        return result
    portal = target.get("portal", "custom")
    portal_scores = get_portal_scores()
    result = portal_scores.get(portal, 6)
    if explain:
        mapped = "mapped" if portal in portal_scores else "default"
        return result, f"portal={portal} -> {result} ({mapped})"
    return result


def _get_effort_base_from_market(track: str) -> int:
    """Map track acceptance/response rate to effort_to_value base."""
    hardcoded_fallback = {
        "emergency": 8,
        "writing": 7,
        "prize": 6,
        "grant": 5,
        "fellowship": 5,
        "residency": 5,
        "program": 5,
        "consulting": 6,
        "job": 6,
        "academic": 5,
    }
    intel = load_market_intelligence()
    data = intel.get("track_benchmarks", {}).get(track, {})
    rate = data.get("acceptance_rate") or data.get("cold_response_rate")
    if rate is None:
        return hardcoded_fallback.get(track, 5)
    if rate >= 0.15:
        return 8
    if rate >= 0.10:
        return 7
    if rate >= 0.07:
        return 6
    if rate >= 0.04:
        return 5
    return 4


def score_effort_to_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Estimate effort-to-value from amount, track, and blocks coverage."""
    amount = entry.get("amount", {})
    value = amount.get("value", 0) if isinstance(amount, dict) else 0
    track = entry.get("track", "")

    submission = entry.get("submission", {})
    blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0

    fit = entry.get("fit", {})
    position = fit.get("identity_position", "") if isinstance(fit, dict) else ""
    position_expected_blocks = {
        "independent-engineer": 5,
        "creative-technologist": 6,
        "systems-artist": 6,
        "educator": 5,
        "community-practitioner": 5,
    }
    expected_blocks = position_expected_blocks.get(position, 6)
    coverage_bonus = min(blocks_count / expected_blocks, 1.0) * 2

    base = _get_effort_base_from_market(track)
    explain_parts = [f"track={track} base={base}"]

    if value >= 50000:
        base += 1
        explain_parts.append(f"${value:,}>=50K (+1)")
    elif value == 0 and track not in ("residency", "program"):
        base -= 1
        explain_parts.append("$0 (-1)")

    explain_parts.append(f"{blocks_count} blocks (+{coverage_bonus:.1f})")

    score = base + coverage_bonus

    if track == "job":
        channel = (entry.get("conversion") or {}).get("channel", "direct") or "direct"
        channel_adj = {
            "referral": 2,
            "indeed": 1,
            "company_career_page": 1,
            "linkedin_easy_apply": -2,
            "linkedin": -1,
        }.get(channel, 0)
        if channel_adj:
            score += channel_adj
            sign = "+" if channel_adj > 0 else ""
            explain_parts.append(f"channel={channel} ({sign}{channel_adj})")

    target = entry.get("target", {})
    location_class = target.get("location_class", "") if isinstance(target, dict) else ""
    if location_class == "international":
        score -= 3
        explain_parts.append("international (-3)")
    elif location_class == "remote-global":
        score -= 1
        explain_parts.append("remote-global (-1)")

    result = max(1, min(10, round(score)))

    if explain:
        return result, f"{' | '.join(explain_parts)} = {result}"
    return result


_DIFF_COMPOSITE: float | None = None


def _get_differentiation_boost() -> tuple[int, float]:
    """Lazy-load differentiation composite and return (boost, composite)."""
    global _DIFF_COMPOSITE
    if _DIFF_COMPOSITE is None:
        try:
            from funding_scorer import load_startup_profile, score_differentiation

            profile = load_startup_profile()
            intel = load_market_intelligence()
            result = score_differentiation(profile, intel)
            _DIFF_COMPOSITE = result["composite"]
        except Exception:
            _DIFF_COMPOSITE = 0.0
    if _DIFF_COMPOSITE >= 8.5:
        return 2, _DIFF_COMPOSITE
    if _DIFF_COMPOSITE >= 7.0:
        return 1, _DIFF_COMPOSITE
    return 0, _DIFF_COMPOSITE


def score_strategic_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score strategic value from organization prestige, track, and differentiation."""
    org = ""
    target = entry.get("target", {})
    if isinstance(target, dict):
        org = target.get("organization") or ""

    for name, prestige_score in HIGH_PRESTIGE.items():
        if org and name.lower() in org.lower():
            if explain:
                return prestige_score, f'org "{org}" matched "{name}" -> {prestige_score} (prestige list)'
            return prestige_score

    track = entry.get("track", "")
    strategic_base = get_strategic_base()
    base = strategic_base.get(track, 5)
    diff_boost, diff_composite = _get_differentiation_boost()
    result = min(10, base + diff_boost)
    if explain:
        source = "track base" if track in strategic_base else "default"
        diff_note = f" + diff_boost={diff_boost} (composite={diff_composite:.1f})" if diff_boost else ""
        return result, f'org "{org}" not in prestige list, track={track} -> {base} ({source}){diff_note} = {result}'
    return result
