"""Explain/review helpers extracted from score.py."""

from __future__ import annotations

from pathlib import Path

RUBRIC_DESCRIPTIONS = {
    "mission_alignment": {
        (1, 2): "Work doesn't fit their stated mission",
        (3, 4): "Tangential connection requiring significant stretching",
        (5, 6): "Plausible fit with some reframing needed",
        (7, 8): "Clear alignment, work fits naturally",
        (9, 10): "Work exemplifies their mission; target applicant",
    },
    "evidence_match": {
        (1, 2): "They want things we can't demonstrate",
        (3, 4): "Most evidence is indirect or requires heavy reframing",
        (5, 6): "Some direct evidence, some gaps",
        (7, 8): "Strong evidence for most requirements",
        (9, 10): "Every requirement has verifiable proof",
    },
    "track_record_fit": {
        (1, 2): "Credentials we don't have and can't reframe",
        (3, 4): "Major gaps (exhibitions, affiliations, team leadership)",
        (5, 6): "Some gaps but reframeable via ORGANVM scale",
        (7, 8): "Credentials match with minor gaps",
        (9, 10): "Credentials exceed expectations",
    },
}


def _rubric_desc(dim: str, score: int) -> str:
    """Return the rubric description for a dimension at a given score."""
    descs = RUBRIC_DESCRIPTIONS.get(dim, {})
    for (lo, hi), desc in descs.items():
        if lo <= score <= hi:
            return desc
    return ""


def explain_entry(
    entry: dict,
    all_entries: list[dict] | None = None,
    *,
    get_weights,
    compute_dimensions,
    compute_composite,
    compute_human_dimensions,
    score_network_proximity,
    score_financial_alignment,
    score_effort_to_value,
    score_strategic_value,
    score_deadline_feasibility,
    score_portal_friction,
    dimension_order: list[str],
) -> str:
    """Generate a detailed score derivation for a single entry."""
    entry_id = entry.get("id", "unknown")
    track = entry.get("track", "")
    rubric = "JOB" if track == "job" else "CREATIVE"
    weights = get_weights(track)
    fit = entry.get("fit", {}) if isinstance(entry.get("fit"), dict) else {}

    lines = []

    dimensions = compute_dimensions(entry, all_entries)
    composite = compute_composite(dimensions, track)
    lines.append(f"{entry_id}: {composite} [{rubric} rubric]")
    lines.append("")

    original = fit.get("original_score")
    current = fit.get("score")
    if original:
        lines.append(f"  original_score: {original} (historical baseline, no longer feeds computation)")
        lines.append(f"  fit.score:      {current} (computed composite)")
    else:
        lines.append(f"  fit.score: {current}")
    lines.append("")

    human_keys = ["mission_alignment", "evidence_match", "track_record_fit"]
    _, signal_explanations = compute_human_dimensions(entry, all_entries, explain=True)

    lines.append("SIGNAL-BASED DIMENSIONS:")
    for key in human_keys:
        dim_val = dimensions[key]
        weight = weights[key]
        lines.append(f"  {key:<25s} {int(dim_val):>2d}  x{weight:.0%}")
        detail = signal_explanations.get(key, "")
        if detail:
            lines.append(detail)

    lines.append("")

    net_val = score_network_proximity(entry, all_entries)
    net_weight = weights.get("network_proximity", 0)
    lines.append("NETWORK PROXIMITY:")
    lines.append(f"  {'network_proximity':<25s} {net_val:>2d}  x{net_weight:.0%}")
    lines.append("")

    auto_funcs = [
        ("financial_alignment", score_financial_alignment),
        ("effort_to_value", score_effort_to_value),
        ("strategic_value", score_strategic_value),
        ("deadline_feasibility", score_deadline_feasibility),
        ("portal_friction", score_portal_friction),
    ]

    lines.append("AUTO DIMENSIONS:")
    for dim_name, func in auto_funcs:
        val, reason = func(entry, explain=True)
        weight = weights.get(dim_name, 0)  # pillar weight sets omit some dims (e.g. grant has no portal_friction)
        lines.append(f"  {dim_name:<25s} {val:>2d}  x{weight:.0%}  <- {reason}")

    lines.append("")

    # Composite breakdown over the track's weighted dimensions. Pillar-specific
    # dims not produced by compute_dimensions fall back to the same neutral
    # default (5) that compute_composite applies, so the terms sum to the score.
    lines.append("COMPOSITE:")
    for dim, weight in weights.items():
        val = dimensions.get(dim, 5)
        lines.append(f"  {dim:<25s} {int(val):>2d} x {weight:.2f} = {val * weight:.2f}")
    lines.append(f"  {'TOTAL':<25s}        = {composite}")

    return "\n".join(lines)


def review_compressed(entries: list[tuple[Path, dict]], lo: float = 6.5, hi: float = 7.5):
    """Print entries in a compressed score band for manual dimension review."""
    compressed = []

    for filepath, data in entries:
        tags = data.get("tags") or []
        if "auto-sourced" in tags:
            continue
        fit = data.get("fit", {}) if isinstance(data.get("fit"), dict) else {}
        score = fit.get("score", 0)
        if lo <= score <= hi:
            compressed.append((filepath, data))

    if not compressed:
        print(f"No entries in the {lo}-{hi} composite band need review.")
        return

    print(f"COMPRESSED SCORE REVIEW ({lo} - {hi} band)")
    print(f"{len(compressed)} entries need human dimension review:\n")

    for filepath, data in sorted(compressed, key=lambda item: item[1].get("fit", {}).get("score", 0), reverse=True):
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        fit = data.get("fit", {})
        score = fit.get("score", 0)
        position = fit.get("identity_position", "—")
        dims = fit.get("dimensions", {}) or {}

        print(f"  {entry_id} ({score}) — {track} — {position}")

        for key in ["mission_alignment", "evidence_match", "track_record_fit"]:
            val = dims.get(key, "?")
            desc = _rubric_desc(key, val) if isinstance(val, int) else ""
            desc_str = f'  ({val}-range: "{desc}")' if desc else ""
            print(f"    {key:<25s} {val}{desc_str}")

        print(f"    -> Review: Are these accurate for {data.get('name', entry_id)} specifically?")
        print()

    print("Edit each YAML's fit.dimensions fields, then run `score.py --all` to recalculate composites.")
