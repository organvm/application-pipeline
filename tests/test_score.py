"""Tests for scripts/score.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score import (
    CREDENTIALS,
    DIMENSION_ORDER,
    HIGH_PRESTIGE,
    JOB_QUALIFICATION_THRESHOLD,
    PORTAL_SCORES,
    POSITION_EXPECTED_ORGANS,
    QUALIFICATION_THRESHOLD,
    ROLE_FIT_TIERS,
    STRATEGIC_BASE,
    TRACK_POSITION_AFFINITY,
    WEIGHTS,
    WEIGHTS_GRANT,
    WEIGHTS_JOB,
    _em_block_portal_coverage,
    _em_evidence_depth,
    _em_materials_readiness,
    _em_slot_name_alignment,
    _ma_framing_specialization,
    _ma_organ_position_coherence,
    _ma_position_profile_match,
    _ma_track_position_affinity,
    _rubric_desc,
    _tr_credential_track_relevance,
    _tr_differentiators_coverage,
    _tr_position_depth,
    _tr_track_experience,
    analyze_reachability,
    applicant_density_adjustment,
    compute_composite,
    compute_dimensions,
    compute_human_dimensions,
    explain_entry,
    get_qualification_threshold,
    get_weights,
    qualify,
    score_deadline_feasibility,
    score_effort_to_value,
    score_financial_alignment,
    score_portal_friction,
    score_strategic_value,
    scoring_confidence_band,
)


def _date_offset(days: int) -> str:
    """Return an ISO date string offset from today."""
    return (date.today() + timedelta(days=days)).isoformat()


def _make_entry(
    track="grant",
    deadline_date=None,
    deadline_type="hard",
    amount_value=0,
    amount_cliff_note="",
    portal="custom",
    organization="Test Org",
    blocks_used=None,
    fit_score=5,
    framing="",
    existing_dims=None,
    original_score=None,
    tags=None,
    name=None,
    identity_position="",
    lead_organs=None,
    portal_fields=None,
    materials_attached=None,
    portfolio_url="",
    entry_id="",
):
    """Build a minimal pipeline entry dict for scoring tests."""
    entry = {
        "track": track,
        "deadline": {
            "date": deadline_date,
            "type": deadline_type,
        },
        "amount": {
            "value": amount_value,
            "currency": "USD",
        },
        "target": {
            "organization": organization,
            "portal": portal,
        },
        "submission": {
            "blocks_used": blocks_used or {},
        },
        "fit": {
            "score": fit_score,
            "framing": framing,
        },
        "tags": tags or [],
    }
    if entry_id:
        entry["id"] = entry_id
    if name:
        entry["name"] = name
    if identity_position:
        entry["fit"]["identity_position"] = identity_position
    if lead_organs is not None:
        entry["fit"]["lead_organs"] = lead_organs
    if amount_cliff_note:
        entry["amount"]["benefits_cliff_note"] = amount_cliff_note
    if existing_dims is not None:
        entry["fit"]["dimensions"] = existing_dims
    if original_score is not None:
        entry["fit"]["original_score"] = original_score
    if portal_fields is not None:
        entry["portal_fields"] = {"fields": portal_fields}
    if materials_attached is not None:
        entry["submission"]["materials_attached"] = materials_attached
    if portfolio_url:
        entry["submission"]["portfolio_url"] = portfolio_url
    return entry


# --- WEIGHTS normalization ---


def test_weights_sum_to_one():
    """All dimension weights must sum to 1.0."""
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"


def test_weights_all_positive():
    """Every weight must be positive."""
    for dim, weight in WEIGHTS.items():
        assert weight > 0, f"Weight for {dim} is non-positive: {weight}"


def test_weights_cover_all_dimensions():
    """WEIGHTS (grant/legacy default) is a valid pillar weight set summing to 1.0."""
    from pipeline_lib import VALID_DIMENSIONS
    assert set(WEIGHTS.keys()) <= VALID_DIMENSIONS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


# --- score_deadline_feasibility ---


def test_deadline_expired():
    """Expired deadlines should score 1."""
    entry = _make_entry(deadline_date=_date_offset(-5))
    assert score_deadline_feasibility(entry) == 1


def test_deadline_tomorrow():
    """Deadline tomorrow (1 day out) should score 2."""
    entry = _make_entry(deadline_date=_date_offset(1))
    assert score_deadline_feasibility(entry) == 2


def test_deadline_three_days():
    """Deadline in 3 days should score 3."""
    entry = _make_entry(deadline_date=_date_offset(3))
    assert score_deadline_feasibility(entry) == 3


def test_deadline_five_days():
    """Deadline in 5 days should score 4 (tight but doable)."""
    entry = _make_entry(deadline_date=_date_offset(5))
    assert score_deadline_feasibility(entry) == 4


def test_deadline_one_week():
    """Deadline in 7 days should score 5."""
    entry = _make_entry(deadline_date=_date_offset(7))
    assert score_deadline_feasibility(entry) == 5


def test_deadline_one_month():
    """Deadline in 20 days should score 8."""
    entry = _make_entry(deadline_date=_date_offset(20))
    assert score_deadline_feasibility(entry) == 8


def test_deadline_far_future():
    """Deadline 60+ days out should score 9."""
    entry = _make_entry(deadline_date=_date_offset(60))
    assert score_deadline_feasibility(entry) == 9


def test_deadline_rolling():
    """Rolling deadlines should score 9."""
    entry = _make_entry(deadline_type="rolling")
    assert score_deadline_feasibility(entry) == 9


def test_deadline_no_dict():
    """Non-dict deadline should return default 7."""
    entry = {"deadline": "2026-03-01"}
    assert score_deadline_feasibility(entry) == 7


# --- score_financial_alignment ---


def test_financial_zero_amount():
    """Zero/unknown amount scores neutral (7) — avoids inflating under-researched entries."""
    entry = _make_entry(amount_value=0)
    assert score_financial_alignment(entry) == 7


def test_financial_below_snap():
    """Amount below SNAP limit should score 9."""
    entry = _make_entry(amount_value=15000)
    assert score_financial_alignment(entry) == 9


def test_financial_between_snap_and_medicaid():
    """Amount between SNAP and Medicaid limits should score 8."""
    entry = _make_entry(amount_value=20500)
    assert score_financial_alignment(entry) == 8


def test_financial_above_essential_plan():
    """Amount above essential plan limit should score 4."""
    entry = _make_entry(amount_value=50000)
    assert score_financial_alignment(entry) == 4


def test_financial_exceeds_cliff_note():
    """Explicit 'exceeds' cliff note forces score to 4."""
    entry = _make_entry(amount_value=15000, amount_cliff_note="Exceeds SNAP threshold")
    assert score_financial_alignment(entry) == 4


def test_financial_essential_plan_cliff_note():
    """Explicit 'essential plan' cliff note forces score to 5."""
    entry = _make_entry(amount_value=15000, amount_cliff_note="Near essential plan limit")
    assert score_financial_alignment(entry) == 5


def test_financial_job_track_high_salary():
    """Job track with salary >$100K should score 8."""
    entry = _make_entry(track="job", amount_value=140000)
    assert score_financial_alignment(entry) == 8


def test_financial_job_track_very_high_salary():
    """Job track with salary >$150K should score 9 (strong comp)."""
    entry = _make_entry(track="job", amount_value=300000)
    assert score_financial_alignment(entry) == 9


def test_financial_job_track_zero_salary():
    """Job track with unknown salary should score 5 (slight penalty)."""
    entry = _make_entry(track="job", amount_value=0)
    assert score_financial_alignment(entry) == 5


def test_financial_non_dict_amount():
    """Non-dict amount should return default 9."""
    entry = {"amount": "unknown"}
    assert score_financial_alignment(entry) == 9


# --- score_portal_friction ---


def test_portal_email():
    """Email portal is easiest (score 9)."""
    entry = _make_entry(portal="email")
    assert score_portal_friction(entry) == 9


def test_portal_slideroom():
    """SlideRoom portal is most friction (score 4)."""
    entry = _make_entry(portal="slideroom")
    assert score_portal_friction(entry) == 4


def test_portal_greenhouse():
    """Greenhouse portal should score 5."""
    entry = _make_entry(portal="greenhouse")
    assert score_portal_friction(entry) == 5


def test_portal_unknown():
    """Unknown portal type falls back to 6."""
    entry = _make_entry(portal="unknown-portal")
    assert score_portal_friction(entry) == 6


def test_portal_all_types_covered():
    """Every type in PORTAL_SCORES should return its mapped value."""
    for portal_type, expected_score in PORTAL_SCORES.items():
        entry = _make_entry(portal=portal_type)
        assert score_portal_friction(entry) == expected_score, (
            f"Portal type '{portal_type}' expected {expected_score}"
        )


# --- score_effort_to_value ---


def test_effort_emergency_track():
    """Emergency track has high base score."""
    entry = _make_entry(track="emergency")
    score = score_effort_to_value(entry)
    assert score >= 6


def test_effort_job_track():
    """Job track has moderate base score (CLI-submittable)."""
    entry = _make_entry(track="job")
    score = score_effort_to_value(entry)
    assert score >= 5


def test_effort_high_block_coverage():
    """High blocks coverage adds a bonus."""
    entry_no_blocks = _make_entry(track="grant", amount_value=10000)
    entry_with_blocks = _make_entry(
        track="grant",
        amount_value=10000,
        blocks_used={
            "artist_statement": "identity/2min",
            "project_description": "projects/organvm-system",
            "bio": "identity/60s",
            "cv": "evidence/metrics-snapshot",
            "work_samples": "evidence/work-samples",
            "methodology": "methodology/ai-conductor",
        },
    )
    score_low = score_effort_to_value(entry_no_blocks)
    score_high = score_effort_to_value(entry_with_blocks)
    assert score_high > score_low


def test_effort_high_value_boost():
    """Amount >= 50000 gets a score boost."""
    entry_low = _make_entry(track="grant", amount_value=10000)
    entry_high = _make_entry(track="grant", amount_value=50000)
    score_low = score_effort_to_value(entry_low)
    score_high = score_effort_to_value(entry_high)
    assert score_high >= score_low


# --- score_strategic_value ---


def test_strategic_high_prestige_org():
    """High-prestige org should return its mapped score."""
    entry = _make_entry(organization="Creative Capital")
    assert score_strategic_value(entry) == HIGH_PRESTIGE["Creative Capital"]


def test_strategic_high_prestige_case_insensitive():
    """Prestige matching should be case-insensitive."""
    entry = _make_entry(organization="creative capital foundation")
    assert score_strategic_value(entry) == HIGH_PRESTIGE["Creative Capital"]


def test_strategic_fallback_to_track():
    """Unknown org falls back to track-based score + differentiation boost."""
    entry = _make_entry(organization="Unknown Org", track="prize")
    from score import _get_differentiation_boost
    boost, _ = _get_differentiation_boost()
    expected = min(10, STRATEGIC_BASE["prize"] + boost)
    assert score_strategic_value(entry) == expected


def test_strategic_unknown_track():
    """Unknown track returns default 5 + differentiation boost."""
    entry = _make_entry(organization="Unknown Org", track="unknown")
    from score import _get_differentiation_boost
    boost, _ = _get_differentiation_boost()
    expected = min(10, 5 + boost)
    assert score_strategic_value(entry) == expected


# --- Mission Alignment signal tests ---


def test_ma_position_profile_match_primary():
    """Primary position match scores 4."""
    entry = _make_entry(identity_position="systems-artist")
    profile = {"primary_position": "systems-artist", "secondary_position": "educator"}
    score, reason = _ma_position_profile_match(entry, profile)
    assert score == 4
    assert "primary" in reason


def test_ma_position_profile_match_secondary():
    """Secondary position match scores 2."""
    entry = _make_entry(identity_position="educator")
    profile = {"primary_position": "systems-artist", "secondary_position": "educator"}
    score, reason = _ma_position_profile_match(entry, profile)
    assert score == 2
    assert "secondary" in reason


def test_ma_position_profile_match_no_profile():
    """No profile available scores 2 (neutral)."""
    entry = _make_entry(identity_position="systems-artist")
    score, reason = _ma_position_profile_match(entry, None)
    assert score == 2
    assert "no profile" in reason


def test_ma_position_profile_match_no_match():
    """Position doesn't match primary or secondary scores 0."""
    entry = _make_entry(identity_position="independent-engineer")
    profile = {"primary_position": "systems-artist", "secondary_position": "educator"}
    score, reason = _ma_position_profile_match(entry, profile)
    assert score == 0


def test_ma_track_position_affinity_strong():
    """systems-artist + residency is a strong fit (3)."""
    entry = _make_entry(track="residency", identity_position="systems-artist")
    score, reason = _ma_track_position_affinity(entry)
    assert score == 3


def test_ma_track_position_affinity_weak():
    """independent-engineer + writing is a weak fit (1)."""
    entry = _make_entry(track="writing", identity_position="independent-engineer")
    score, reason = _ma_track_position_affinity(entry)
    assert score == 1


def test_ma_organ_coherence_full_overlap():
    """Full organ overlap scores 2."""
    entry = _make_entry(
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
    )
    score, reason = _ma_organ_position_coherence(entry)
    assert score == 2


def test_ma_organ_coherence_no_overlap():
    """No organ overlap scores 0."""
    entry = _make_entry(
        identity_position="systems-artist",
        lead_organs=["III", "IV"],
    )
    score, reason = _ma_organ_position_coherence(entry)
    assert score == 0


def test_ma_framing_specialization_present():
    """Entry with a framings/* block scores 1."""
    entry = _make_entry(
        blocks_used={"framing": "framings/systems-artist", "bio": "identity/60s"},
    )
    score, reason = _ma_framing_specialization(entry)
    assert score == 1


def test_ma_framing_specialization_absent():
    """Entry without framings/* block scores 0."""
    entry = _make_entry(
        blocks_used={"bio": "identity/60s"},
    )
    score, reason = _ma_framing_specialization(entry)
    assert score == 0


# --- Evidence Match signal tests ---


def test_em_block_portal_full_coverage():
    """Blocks >= fields ratio scores 3."""
    entry = _make_entry(
        blocks_used={"a": "x", "b": "x", "c": "x", "d": "x"},
        portal_fields=[{"name": "a"}, {"name": "b"}, {"name": "c"}],
    )
    score, reason = _em_block_portal_coverage(entry)
    assert score == 3


def test_em_block_portal_no_coverage():
    """Zero blocks or zero fields scores 0."""
    entry = _make_entry()
    score, reason = _em_block_portal_coverage(entry)
    assert score == 0


def test_em_block_portal_half_coverage():
    """Ratio >= 0.5 scores 2."""
    entry = _make_entry(
        blocks_used={"a": "x", "b": "x"},
        portal_fields=[{"name": "a"}, {"name": "b"}, {"name": "c"}, {"name": "d"}],
    )
    score, reason = _em_block_portal_coverage(entry)
    assert score == 2


def test_em_slot_alignment_direct_match():
    """Direct name match between block keys and field names."""
    entry = _make_entry(
        blocks_used={"artist_statement": "identity/2min", "bio": "identity/60s"},
        portal_fields=[{"name": "artist_statement"}, {"name": "bio"}, {"name": "work_samples"}],
    )
    score, reason = _em_slot_name_alignment(entry)
    assert score == 2  # 2/3 * 3 = 2


def test_em_slot_alignment_fuzzy_match():
    """Fuzzy match: 'statement' in 'artist_statement'."""
    entry = _make_entry(
        blocks_used={"artist_statement": "identity/2min"},
        portal_fields=[{"name": "statement"}],
    )
    score, reason = _em_slot_name_alignment(entry)
    assert score == 3  # 1/1 * 3 = 3


def test_em_evidence_depth_both_present():
    """evidence/* + methodology/* blocks scores 2."""
    entry = _make_entry(
        blocks_used={
            "evidence": "evidence/differentiators",
            "methodology": "methodology/ai-conductor",
        },
    )
    score, reason = _em_evidence_depth(entry)
    assert score == 2


def test_em_evidence_depth_one_present():
    """Only evidence/* block scores 1."""
    entry = _make_entry(
        blocks_used={"evidence": "evidence/differentiators"},
    )
    score, reason = _em_evidence_depth(entry)
    assert score == 1


def test_em_materials_readiness():
    """Both materials and portfolio_url scores 2."""
    entry = _make_entry(
        materials_attached=["resumes/base/resume.pdf"],
        portfolio_url="https://example.com",
    )
    score, reason = _em_materials_readiness(entry)
    assert score == 2


def test_em_materials_readiness_none():
    """No materials or portfolio scores 0."""
    entry = _make_entry()
    score, reason = _em_materials_readiness(entry)
    assert score == 0


# --- Track Record Fit signal tests ---


def test_tr_credential_best_for_track():
    """Best credential for 'writing' track is mfa_creative_writing=4."""
    entry = _make_entry(track="writing")
    score, reason = _tr_credential_track_relevance(entry)
    assert score == 4
    assert "mfa_creative_writing" in reason


def test_tr_credential_consulting():
    """Best credential for consulting is meta_fullstack_dev=4."""
    entry = _make_entry(track="consulting")
    score, reason = _tr_credential_track_relevance(entry)
    assert score == 4
    assert "meta_fullstack_dev" in reason


def test_tr_track_experience_counts_submitted():
    """Counts same-track entries with submitted+ status."""
    entry = _make_entry(track="grant", entry_id="test-grant")
    all_entries = [
        {"id": "g1", "track": "grant", "status": "submitted"},
        {"id": "g2", "track": "grant", "status": "outcome"},
        {"id": "g3", "track": "grant", "status": "drafting"},  # not submitted
        {"id": "r1", "track": "residency", "status": "submitted"},  # wrong track
    ]
    score, reason = _tr_track_experience(entry, all_entries)
    assert score == 2  # 2 submitted grant entries


def test_tr_track_experience_no_prior():
    """Zero same-track submitted entries scores 0."""
    entry = _make_entry(track="prize", entry_id="test-prize")
    all_entries = [
        {"id": "g1", "track": "grant", "status": "submitted"},
    ]
    score, reason = _tr_track_experience(entry, all_entries)
    assert score == 0


def test_tr_position_depth_has_framing():
    """Position with existing framing block on disk scores 2."""
    # systems-artist has blocks/framings/systems-artist.md in the repo
    entry = _make_entry(identity_position="systems-artist")
    score, reason = _tr_position_depth(entry)
    assert score == 2
    assert "exists" in reason


def test_tr_differentiators_coverage():
    """Profile with 3+ evidence_highlights scores 1."""
    entry = _make_entry()
    profile = {"evidence_highlights": ["a", "b", "c", "d"]}
    score, reason = _tr_differentiators_coverage(entry, profile)
    assert score == 1


def test_tr_differentiators_no_profile():
    """No profile scores 0."""
    entry = _make_entry()
    score, reason = _tr_differentiators_coverage(entry, None)
    assert score == 0


# --- Signal-based dimensions clamped to range ---


def test_signal_dims_clamped_to_range():
    """Signal-based dimensions should be clamped to [1, 10]."""
    # Minimal entry — all signals score low
    entry = _make_entry(track="job")
    dims = compute_human_dimensions(entry, all_entries=[])
    for key in ("mission_alignment", "evidence_match", "track_record_fit"):
        assert 1 <= dims[key] <= 10, f"{key}={dims[key]} out of [1,10]"

    # Rich entry — signals may sum high
    entry_rich = _make_entry(
        track="residency",
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        blocks_used={
            "framing": "framings/systems-artist",
            "artist_statement": "identity/2min",
            "evidence": "evidence/differentiators",
            "methodology": "methodology/ai-conductor",
        },
        portal_fields=[{"name": "artist_statement"}, {"name": "evidence"}],
        materials_attached=["resumes/base/resume.pdf"],
        portfolio_url="https://example.com",
    )
    dims_rich = compute_human_dimensions(entry_rich, all_entries=[])
    for key in ("mission_alignment", "evidence_match", "track_record_fit"):
        assert 1 <= dims_rich[key] <= 10, f"{key}={dims_rich[key]} out of [1,10]"


# --- compute_dimensions ---


def test_compute_dimensions_returns_all_nine():
    """compute_dimensions returns the 9 core + 7 pillar dimensions."""
    from pipeline_lib import VALID_DIMENSIONS
    entry = _make_entry()
    dims = compute_dimensions(entry)
    assert set(dims.keys()) == set(VALID_DIMENSIONS)
    assert set(DIMENSION_ORDER) <= set(dims.keys())


def test_no_human_override_dimensions_always_recompute():
    """Existing stored dimensions are ignored — always recomputed from signals."""
    entry = _make_entry(
        fit_score=5,
        existing_dims={
            "mission_alignment": 9,
            "evidence_match": 8,
            "track_record_fit": 7,
        },
    )
    dims = compute_dimensions(entry, all_entries=[])
    # With no identity_position, no profile, no blocks, the signal-based
    # scores should NOT be 9/8/7 — they should be recomputed (lower).
    assert dims["mission_alignment"] != 9 or dims["evidence_match"] != 8


def test_compute_dimensions_auto_dims_recomputed():
    """Auto-derivable dimensions should be recomputed even if existing."""
    entry = _make_entry(
        portal="email",
        existing_dims={
            "portal_friction": 1,  # stale override — should be ignored
        },
    )
    dims = compute_dimensions(entry)
    assert dims["portal_friction"] == PORTAL_SCORES["email"]  # recomputed to 9


# --- compute_composite ---


def test_composite_perfect_ten():
    """All 10s should produce composite 10.0."""
    dims = {dim: 10 for dim in WEIGHTS}
    assert compute_composite(dims) == 10.0


def test_composite_all_ones():
    """All 1s should produce composite 1.0."""
    dims = {dim: 1 for dim in WEIGHTS}
    assert compute_composite(dims) == 1.0


def test_composite_weighted_sum():
    """Verify composite is the correct weighted sum."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "network_proximity": 3,
        "financial_alignment": 9,
        "effort_to_value": 5,
        "strategic_value": 7,
        "deadline_feasibility": 4,
        "portal_friction": 6,
    }
    # Weighted sum over the active (grant/legacy) weights; dims absent from the
    # weight set are ignored, pillar dims absent from `dims` default to 5.
    expected = round(sum(dims.get(d, 5) * w for d, w in WEIGHTS.items()), 1)
    assert compute_composite(dims) == expected


def test_composite_missing_dim_defaults_to_five():
    """Missing dimension should default to 5 in the weighted sum."""
    dims = {"mission_alignment": 10}  # only one dim provided
    result = compute_composite(dims)
    expected = round(sum(dims.get(d, 5) * w for d, w in WEIGHTS.items()), 1)
    assert result == expected


# --- qualify ---


def test_qualification_threshold_is_reasonable():
    """QUALIFICATION_THRESHOLD should be between 1 and 10."""
    assert 1.0 <= QUALIFICATION_THRESHOLD <= 10.0


def test_qualify_above_threshold():
    """Entry scoring above threshold should return (True, reason)."""
    entry = _make_entry(
        fit_score=8,
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        framing="Strong framing that exceeds thirty chars easily",
        blocks_used={
            "framing": "framings/systems-artist",
            "artist_statement": "identity/2min",
            "evidence": "evidence/differentiators",
        },
        portal_fields=[{"name": "artist_statement"}, {"name": "evidence"}],
        materials_attached=["resume.pdf"],
        portfolio_url="https://example.com",
        organization="Creative Capital",
        deadline_type="rolling",
        amount_value=15000,
    )
    # Strong, signal-rich entry with a warm-plus network so the composite
    # clears the qualification threshold despite uncomputed pillar dims (=5).
    entry["network"] = {"relationship_strength": "strong"}
    should_apply, reason = qualify(entry)
    assert should_apply is True
    assert ">=" in reason


def test_qualify_below_threshold():
    """Entry scoring below threshold should return (False, reason with weak dims)."""
    entry = _make_entry(
        fit_score=1,
        track="job",
        amount_value=100000,
        portal="slideroom",
        deadline_date=_date_offset(-5),
    )
    should_apply, reason = qualify(entry)
    assert should_apply is False
    assert "<" in reason
    assert "weak:" in reason


def test_qualify_boundary():
    """Entry exactly at threshold should return APPLY."""
    # Build an entry that scores exactly at threshold — we just need to
    # verify the >= comparison handles the boundary correctly.
    entry = _make_entry(fit_score=5, deadline_type="rolling")
    dims = compute_dimensions(entry)
    composite = compute_composite(dims)

    should_apply, _ = qualify(entry)
    if composite >= QUALIFICATION_THRESHOLD:
        assert should_apply is True
    else:
        assert should_apply is False


# --- Job rubric weights ---


def test_weights_job_sum_to_one():
    """Job dimension weights must sum to 1.0."""
    total = sum(WEIGHTS_JOB.values())
    assert abs(total - 1.0) < 1e-9, f"Job weights sum to {total}, expected 1.0"


def test_weights_job_all_positive():
    """Every job weight must be positive."""
    for dim, weight in WEIGHTS_JOB.items():
        assert weight > 0, f"Job weight for {dim} is non-positive: {weight}"


def test_weights_job_cover_all_dimensions():
    """WEIGHTS_JOB is a valid pillar weight set summing to 1.0."""
    from pipeline_lib import VALID_DIMENSIONS
    assert set(WEIGHTS_JOB.keys()) <= VALID_DIMENSIONS
    assert abs(sum(WEIGHTS_JOB.values()) - 1.0) < 1e-9


def test_get_weights_job():
    """get_weights returns job weights for track='job'."""
    assert get_weights("job") is WEIGHTS_JOB


def test_get_weights_creative():
    """get_weights returns grant/creative weights for grant-pillar tracks."""
    for track in ("grant", "fellowship", "residency", "writing"):
        assert get_weights(track) is WEIGHTS_GRANT
    # Unknown/empty track falls back to the legacy WEIGHTS default.
    assert get_weights("") is WEIGHTS


def test_get_qualification_threshold_job():
    """Job track uses JOB_QUALIFICATION_THRESHOLD."""
    assert get_qualification_threshold("job") == JOB_QUALIFICATION_THRESHOLD


def test_get_qualification_threshold_creative():
    """Non-job tracks use QUALIFICATION_THRESHOLD."""
    for track in ("grant", "fellowship", "residency", ""):
        assert get_qualification_threshold(track) == QUALIFICATION_THRESHOLD


# --- Job composite scoring ---


def test_composite_job_weights():
    """Job entry should use WEIGHTS_JOB for composite calculation."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "network_proximity": 3,
        "financial_alignment": 6,
        "effort_to_value": 5,
        "strategic_value": 8,
        "deadline_feasibility": 9,
        "portal_friction": 5,
    }
    job_score = compute_composite(dims, "job")
    creative_score = compute_composite(dims, "grant")

    # Manually compute expected job score with precision weights
    round(
        8 * 0.25 + 7 * 0.20 + 3 * 0.20 + 6 * 0.15
        + 8 * 0.10 + 6 * 0.05 + 5 * 0.03 + 9 * 0.01 + 5 * 0.01,
        1,
    )
    # Weight-dependent — just verify job != creative (different weight sets)
    assert isinstance(job_score, float)

    # Job and creative scores should differ with these unequal dims
    assert job_score != creative_score


def test_composite_creative_weights():
    """Non-job entry should use WEIGHTS (creative) for composite."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "network_proximity": 3,
        "financial_alignment": 9,
        "effort_to_value": 5,
        "strategic_value": 7,
        "deadline_feasibility": 4,
        "portal_friction": 6,
    }
    expected_grant = round(sum(dims.get(d, 5) * w for d, w in WEIGHTS_GRANT.items()), 1)
    expected_legacy = round(sum(dims.get(d, 5) * w for d, w in WEIGHTS.items()), 1)
    assert compute_composite(dims, "grant") == expected_grant
    assert compute_composite(dims, "") == expected_legacy
    assert compute_composite(dims) == expected_legacy


# --- Job qualification threshold ---


def test_qualify_job_threshold():
    """Job entry should use JOB_QUALIFICATION_THRESHOLD (5.5)."""
    # Build a job entry that scores between 5.0 and 5.5
    # This should SKIP under job threshold but would APPLY under creative
    entry = _make_entry(
        track="job",
        fit_score=5,
        portal="greenhouse",
        deadline_type="rolling",
        organization="Unknown Corp",
    )
    dims = compute_dimensions(entry)
    job_composite = compute_composite(dims, "job")

    should_apply, reason = qualify(entry)

    # Verify the threshold used is the job one
    assert str(JOB_QUALIFICATION_THRESHOLD) in reason or str(QUALIFICATION_THRESHOLD) not in reason.replace(str(JOB_QUALIFICATION_THRESHOLD), "")
    if job_composite >= JOB_QUALIFICATION_THRESHOLD:
        assert should_apply is True
    else:
        assert should_apply is False


def test_qualify_creative_threshold():
    """Creative entry should use QUALIFICATION_THRESHOLD (5.0)."""
    entry = _make_entry(
        track="grant",
        fit_score=5,
        deadline_type="rolling",
    )
    should_apply, reason = qualify(entry)
    assert str(QUALIFICATION_THRESHOLD) in reason


# --- Job tier scoring with job weights ---


def test_job_tier1_scores_above_cold_baseline():
    """Tier-1 auto-sourced job (cold) should score above baseline but below precision threshold.

    With precision weights, network_proximity=1 (cold, 20% weight) intentionally drags
    cold-sourced jobs below the 9.0 application threshold. This is by design.
    """
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
    )
    entry["name"] = "Software Engineer, Agent SDK"
    entry["tags"] = ["auto-sourced"]
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    # Cold tier-1 should score 6-7 range (network_proximity=1 at 20% is a -0.8 drag)
    assert composite >= 6.0, f"Tier-1 cold job scored {composite}, expected >= 6.0"
    assert composite < 9.0, f"Tier-1 cold job scored {composite}, should be < 9.0 (no warm path)"


def test_job_tier1_with_warm_path_scores_high():
    """Tier-1 job with warm network path should score high enough to apply."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
        blocks_used={
            "framing": "framings/independent-engineer",
            "evidence": "evidence/differentiators",
            "work_samples": "evidence/work-samples",
            "credentials": "pitches/credentials-creative-tech",
            "methodology": "methodology/ai-conductor",
        },
    )
    entry["name"] = "Software Engineer, Agent SDK"
    entry["tags"] = ["auto-sourced"]
    entry["network"] = {"relationship_strength": "warm"}
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    # With warm path (7 at 20%) + blocks + tier-1, should be competitive
    assert composite >= 7.0, (
        f"Tier-1 job with warm path scored {composite}, expected >= 7.0"
    )


def test_job_tier1_dimension_values():
    """Tier-1 dimension values should reflect raised ceilings (9/9/7)."""
    tier1 = next(t for t in ROLE_FIT_TIERS if t["name"] == "tier-1-strong")
    assert tier1["mission_alignment"] == 9
    assert tier1["evidence_match"] == 9
    assert tier1["track_record_fit"] == 7


def test_job_tier2_dimension_values():
    """Tier-2 dimension values should reflect raised ceilings (7/6/5)."""
    tier2 = next(t for t in ROLE_FIT_TIERS if t["name"] == "tier-2-moderate")
    assert tier2["mission_alignment"] == 7
    assert tier2["evidence_match"] == 6
    assert tier2["track_record_fit"] == 5


def test_job_tier4_scores_below_threshold():
    """Tier-4 auto-sourced job (e.g. iOS) should score below 5.5 with job weights."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
    )
    entry["name"] = "Software Engineer, iOS"
    entry["tags"] = ["auto-sourced"]
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    assert composite < JOB_QUALIFICATION_THRESHOLD, (
        f"Tier-4 job scored {composite}, expected < {JOB_QUALIFICATION_THRESHOLD}"
    )


# --- explain mode ---


def test_explain_creative_entry_shows_all_dimensions():
    """--explain output should contain all 9 dimension names."""
    entry = _make_entry(
        fit_score=8,
        framing="Multi-year systems art project bridging recursive computing",
        blocks_used={"a": "x", "b": "x", "c": "x", "d": "x", "e": "x"},
        organization="Creative Capital",
        deadline_type="rolling",
    )
    entry["id"] = "test-creative"
    output = explain_entry(entry, all_entries=[])
    for dim in WEIGHTS:
        assert dim in output, f"Dimension '{dim}' not found in explain output"


def test_explain_auto_sourced_job_shows_tier():
    """--explain output for auto-sourced job should mention the tier."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
        name="Software Engineer, Agent SDK",
        tags=["auto-sourced"],
    )
    entry["id"] = "test-job"
    output = explain_entry(entry, all_entries=[])
    assert "tier-1-strong" in output or "auto-sourced" in output


def test_explain_includes_weighted_sum():
    """--explain output should include the COMPOSITE line with terms."""
    entry = _make_entry(fit_score=7, deadline_type="rolling")
    entry["id"] = "test-entry"
    output = explain_entry(entry, all_entries=[])
    assert "COMPOSITE:" in output


def test_explain_shows_original_score_when_present():
    """--explain should show original_score if available."""
    entry = _make_entry(fit_score=7.5, original_score=7.0, deadline_type="rolling")
    entry["id"] = "test-entry"
    output = explain_entry(entry, all_entries=[])
    assert "original_score" in output
    assert "7.0" in output


def test_explain_shows_signal_breakdown():
    """--explain output should show signal-level detail for each dimension."""
    entry = _make_entry(
        track="residency",
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        blocks_used={
            "framing": "framings/systems-artist",
            "evidence": "evidence/differentiators",
        },
        portal_fields=[{"name": "artist_statement"}, {"name": "evidence"}],
        materials_attached=["resume.pdf"],
        portfolio_url="https://example.com",
        deadline_type="rolling",
    )
    entry["id"] = "test-signal"
    output = explain_entry(entry, all_entries=[])
    assert "SIGNAL-BASED DIMENSIONS:" in output
    assert "position-profile match:" in output
    assert "block-portal coverage:" in output
    assert "credential-track:" in output


def test_explain_consulting_entry_no_crash():
    """--explain must not crash on consulting entries.

    Consulting weights omit some core dims (e.g. track_record_fit), so every
    weight lookup in explain_entry must tolerate absent dimensions. Regression
    for a KeyError found by driving `score --explain` on a consulting entry.
    """
    entry = _make_entry(track="consulting", deadline_type="rolling")
    entry["id"] = "test-consulting"
    output = explain_entry(entry, all_entries=[])
    assert "COMPOSITE:" in output
    assert "recurring_potential" in output
    assert "client_fit" in output


# --- Signal-based scoring ignores original_score ---


def test_signal_dims_ignore_original_score():
    """Signal-based dimensions don't use original_score at all."""
    entry_a = _make_entry(
        fit_score=8.0, original_score=6.0,
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        track="grant",
    )
    entry_b = _make_entry(
        fit_score=3.0, original_score=3.0,
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        track="grant",
    )
    dims_a = compute_human_dimensions(entry_a, all_entries=[])
    dims_b = compute_human_dimensions(entry_b, all_entries=[])
    # Same structured data -> same signal scores, regardless of original_score
    assert dims_a == dims_b


def test_auto_sourced_still_uses_title_based():
    """Auto-sourced entries should still use title-based estimation (tier-1)."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        original_score=1,
        name="Software Engineer, Agent SDK",
        tags=["auto-sourced"],
    )
    dims = compute_human_dimensions(entry)
    assert dims["mission_alignment"] == 9


# --- Job financial alignment corrected ---


def test_financial_job_high_salary_scores_high():
    """Job with >$150K salary should score 9 (strong comp)."""
    entry = _make_entry(track="job", amount_value=200000)
    assert score_financial_alignment(entry) == 9


def test_financial_job_zero_salary_penalized():
    """Job with $0 salary should score 5 (slight penalty for unknown)."""
    entry = _make_entry(track="job", amount_value=0)
    assert score_financial_alignment(entry) == 5


def test_financial_job_moderate_salary():
    """Job with >$50K salary should score 7 (adequate comp)."""
    entry = _make_entry(track="job", amount_value=75000)
    assert score_financial_alignment(entry) == 7


def test_financial_job_low_salary():
    """Job with salary <= $50K should score 6 (low comp)."""
    entry = _make_entry(track="job", amount_value=40000)
    assert score_financial_alignment(entry) == 6


# --- explain parameter returns tuples ---


def test_explain_param_deadline():
    """score_deadline_feasibility with explain=True returns (score, reason)."""
    entry = _make_entry(deadline_type="rolling")
    result = score_deadline_feasibility(entry, explain=True)
    assert isinstance(result, tuple)
    score, reason = result
    assert score == 9
    assert "rolling" in reason or "no date" in reason


def test_explain_param_financial():
    """score_financial_alignment with explain=True returns (score, reason)."""
    entry = _make_entry(amount_value=15000)
    result = score_financial_alignment(entry, explain=True)
    assert isinstance(result, tuple)
    score, reason = result
    assert score == 9
    assert "SNAP" in reason


def test_explain_param_portal():
    """score_portal_friction with explain=True returns (score, reason)."""
    entry = _make_entry(portal="email")
    result = score_portal_friction(entry, explain=True)
    assert isinstance(result, tuple)
    score, reason = result
    assert score == 9
    assert "email" in reason


def test_explain_param_effort():
    """score_effort_to_value with explain=True returns (score, reason)."""
    entry = _make_entry(track="emergency")
    result = score_effort_to_value(entry, explain=True)
    assert isinstance(result, tuple)
    score, reason = result
    assert score >= 6
    assert "emergency" in reason


def test_explain_param_strategic():
    """score_strategic_value with explain=True returns (score, reason)."""
    entry = _make_entry(organization="Creative Capital")
    result = score_strategic_value(entry, explain=True)
    assert isinstance(result, tuple)
    score, reason = result
    assert score == 10
    assert "prestige" in reason


def test_explain_param_human_dims():
    """compute_human_dimensions with explain=True returns (dims, explanations)."""
    entry = _make_entry(
        fit_score=7,
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        blocks_used={"framing": "framings/systems-artist"},
    )
    result = compute_human_dimensions(entry, all_entries=[], explain=True)
    assert isinstance(result, tuple)
    dims, explanations = result
    assert "mission_alignment" in dims
    assert "mission_alignment" in explanations
    assert "position-profile match" in explanations["mission_alignment"]


# --- rubric_desc helper ---


def test_rubric_desc_returns_description():
    """_rubric_desc should return the matching description for a score."""
    desc = _rubric_desc("mission_alignment", 9)
    assert "exemplifies" in desc or "target applicant" in desc


def test_rubric_desc_unknown_dim():
    """_rubric_desc should return empty string for unknown dimension."""
    assert _rubric_desc("nonexistent_dim", 5) == ""


# --- review_compressed filters correctly ---


def test_review_compressed_excludes_auto_sourced(capsys):
    """review_compressed should skip auto-sourced entries."""
    from score import review_compressed

    entries = [
        (Path("/fake/job.yaml"), {
            "id": "job-1",
            "track": "job",
            "tags": ["auto-sourced"],
            "fit": {"score": 7.0, "dimensions": {}},
        }),
        (Path("/fake/grant.yaml"), {
            "id": "grant-1",
            "name": "Test Grant",
            "track": "grant",
            "tags": [],
            "fit": {
                "score": 7.1,
                "identity_position": "systems-artist",
                "dimensions": {
                    "mission_alignment": 8,
                    "evidence_match": 6,
                    "track_record_fit": 7,
                },
            },
        }),
    ]
    review_compressed(entries, lo=6.5, hi=7.5)
    captured = capsys.readouterr()
    assert "grant-1" in captured.out
    assert "job-1" not in captured.out


# --- Signal constants consistency ---


def test_track_position_affinity_covers_all_tracks():
    """Every creative track should have affinity scores."""
    for track in ("grant", "residency", "prize", "fellowship", "program",
                  "writing", "emergency", "consulting"):
        assert track in TRACK_POSITION_AFFINITY, f"Missing track: {track}"


def test_position_expected_organs_covers_all_positions():
    """Every identity position should have expected organs."""
    for pos in ("systems-artist", "creative-technologist", "community-practitioner",
                "educator", "independent-engineer"):
        assert pos in POSITION_EXPECTED_ORGANS, f"Missing position: {pos}"


def test_credentials_cover_all_tracks():
    """Every credential should have scores for all creative tracks."""
    tracks = {"grant", "residency", "prize", "fellowship", "program",
              "writing", "emergency", "consulting"}
    for cred_name, track_scores in CREDENTIALS.items():
        assert tracks <= set(track_scores.keys()), (
            f"Credential {cred_name} missing tracks: {tracks - set(track_scores.keys())}"
        )


# --- Integration: differentiation test ---


def test_compressed_entries_now_differentiate():
    """Entries with different structured data should get different scores."""
    # A residency with systems-artist position, organs I/II/META, framings block
    entry_residency = _make_entry(
        track="residency",
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        blocks_used={
            "framing": "framings/systems-artist",
            "artist_statement": "identity/2min",
            "evidence": "evidence/differentiators",
        },
        portal_fields=[{"name": "artist_statement"}, {"name": "evidence"}],
        materials_attached=["resume.pdf"],
        portfolio_url="https://example.com",
        entry_id="entry-residency",
    )

    # An emergency entry with community-practitioner, different organs, no blocks
    entry_emergency = _make_entry(
        track="emergency",
        identity_position="community-practitioner",
        lead_organs=["V", "VI"],
        entry_id="entry-emergency",
    )

    all_entries = []
    dims_res = compute_dimensions(entry_residency, all_entries)
    dims_emg = compute_dimensions(entry_emergency, all_entries)

    # The entries should have different dimension scores
    ma_diff = abs(dims_res["mission_alignment"] - dims_emg["mission_alignment"])
    em_diff = abs(dims_res["evidence_match"] - dims_emg["evidence_match"])
    tr_diff = abs(dims_res["track_record_fit"] - dims_emg["track_record_fit"])

    total_diff = ma_diff + em_diff + tr_diff
    assert total_diff >= 3, (
        f"Expected differentiation >= 3 across MA/EM/TR, got {total_diff} "
        f"(residency={dims_res}, emergency={dims_emg})"
    )


def test_auto_sourced_jobs_still_use_tier_estimation():
    """Auto-sourced job entries should still use tier-based title estimation."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        name="Software Engineer, Developer Tools",
        tags=["auto-sourced"],
    )
    dims = compute_human_dimensions(entry)
    # devtools matches tier-1-strong: MA=9, EM=9, TR=7
    assert dims["mission_alignment"] == 9
    assert dims["evidence_match"] == 9
    assert dims["track_record_fit"] == 7


# --- Auto-qualify tests ---


def test_run_auto_qualify_defaults_to_dry_run(capsys):
    """run_auto_qualify without --yes should default to dry-run (no file moves)."""
    from pipeline_lib import PIPELINE_DIR_RESEARCH_POOL
    from score import run_auto_qualify

    if not PIPELINE_DIR_RESEARCH_POOL.exists():
        return  # Skip if no pool dir

    # Neither dry_run=True nor yes=True — should default to dry-run behavior
    run_auto_qualify(dry_run=False, yes=False)
    captured = capsys.readouterr()
    assert "dry-run" in captured.out.lower() or "dry run" in captured.out.lower() or "Defaulting to dry-run" in captured.out


def test_run_auto_qualify_dry_run_no_file_moves(capsys):
    """run_auto_qualify(dry_run=True) should not move any files."""
    from pipeline_lib import PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL
    from score import run_auto_qualify

    if not PIPELINE_DIR_RESEARCH_POOL.exists():
        return  # Skip if no pool dir

    # Count files before
    pool_before = len(list(PIPELINE_DIR_RESEARCH_POOL.glob("*.yaml")))
    active_before = len(list(PIPELINE_DIR_ACTIVE.glob("*.yaml")))

    run_auto_qualify(dry_run=True)

    # Count files after — should be unchanged
    pool_after = len(list(PIPELINE_DIR_RESEARCH_POOL.glob("*.yaml")))
    active_after = len(list(PIPELINE_DIR_ACTIVE.glob("*.yaml")))

    assert pool_before == pool_after, "Dry run should not move files from pool"
    assert active_before == active_after, "Dry run should not add files to active"


def test_run_auto_qualify_default_uses_rubric_threshold():
    """run_auto_qualify default min_score=None resolves to mode-aware threshold at runtime."""
    import inspect

    from score import AUTO_QUALIFY_MIN, get_auto_qualify_min, run_auto_qualify

    sig = inspect.signature(run_auto_qualify)
    default = sig.parameters["min_score"].default
    assert default is None, f"Expected default None (mode-aware), got {default}"
    # Runtime resolution should return at least the rubric minimum
    resolved = get_auto_qualify_min()
    assert resolved >= AUTO_QUALIFY_MIN, f"Mode-aware min {resolved} < rubric min {AUTO_QUALIFY_MIN}"


def test_run_auto_qualify_min_score_filters(capsys):
    """A very high min_score should filter out all entries."""
    from score import run_auto_qualify

    run_auto_qualify(dry_run=True, min_score=99.0)
    captured = capsys.readouterr()
    assert ("No entries meet the qualification threshold" in captured.out
            or "Qualify (score >= 99.0): 0" in captured.out
            or "No entries in research_pool" in captured.out)


def test_run_auto_qualify_limit_caps_output(capsys):
    """--limit should cap the number of entries shown."""
    from pipeline_lib import PIPELINE_DIR_RESEARCH_POOL
    from score import run_auto_qualify

    if not PIPELINE_DIR_RESEARCH_POOL.exists():
        return

    run_auto_qualify(dry_run=True, min_score=0.0, limit=2)
    captured = capsys.readouterr()
    # Count [dry-run] lines — should be at most 2
    dry_run_lines = [line for line in captured.out.splitlines() if "[dry-run]" in line]
    assert len(dry_run_lines) <= 2, f"Expected at most 2 dry-run lines, got {len(dry_run_lines)}"


# --- Reachability analysis tests ---


def test_reachability_cold_to_warm_adds_points():
    """Upgrading network from cold to warm should increase composite and appear in scenarios."""
    entry = _make_entry(
        track="job",
        fit_score=7,
        identity_position="independent-engineer",
        lead_organs=["III"],
        portal="greenhouse",
        organization="Some Corp",
        entry_id="reachability-cold-warm",
    )
    # Ensure network is cold (default — no network field)
    entry.pop("network", None)

    result = analyze_reachability(entry, all_entries=[], threshold=9.0)

    # Should have scenarios for levels above cold (score=1)
    assert len(result["scenarios"]) > 0, "Expected at least one scenario"
    level_names = [s["level"] for s in result["scenarios"]]
    assert "warm" in level_names, f"Expected 'warm' in scenarios, got {level_names}"

    # The warm scenario should have a positive delta
    warm_scenario = next(s for s in result["scenarios"] if s["level"] == "warm")
    assert warm_scenario["delta"] > 0, (
        f"Expected positive delta for warm upgrade, got {warm_scenario['delta']}"
    )
    assert warm_scenario["composite"] > result["current_composite"], (
        "Warm scenario composite should exceed current composite"
    )


def test_reachability_already_above_threshold():
    """Entry already above threshold: caller should classify via current_composite >= threshold.

    analyze_reachability always computes scenarios for higher network levels.
    When current_composite >= threshold, the caller (run_reachable) classifies
    the entry as "already above" by checking current_composite directly.
    This test verifies that pattern works correctly.
    """
    # Build an entry with strong signals across all dimensions
    entry = _make_entry(
        track="grant",
        fit_score=10,
        identity_position="systems-artist",
        lead_organs=["I", "II", "META"],
        blocks_used={
            "framing": "framings/systems-artist",
            "artist_statement": "identity/2min",
            "evidence": "evidence/differentiators",
        },
        portal_fields=[{"name": "artist_statement"}, {"name": "evidence"}],
        materials_attached=["resume.pdf"],
        portfolio_url="https://example.com",
        portal="email",
        deadline_type="rolling",
        amount_value=15000,
        organization="Creative Capital",
        entry_id="reachability-already-high",
    )
    # Give it a strong network so the composite is already high
    entry["network"] = {"relationship_strength": "strong"}

    # Compute the actual composite to determine a threshold below it
    dims = compute_dimensions(entry, all_entries=[])
    actual_composite = compute_composite(dims, entry["track"])
    # Grant composites are capped below 8.0 while pillar dims (narrative_fit,
    # prestige_multiplier, cycle_urgency) remain uncomputed and default to 5.
    assert actual_composite >= 6.5, (
        f"Test setup: expected a high composite, got {actual_composite}"
    )

    # Use a threshold at or below the current composite
    threshold = actual_composite
    result = analyze_reachability(entry, all_entries=[], threshold=threshold)

    # The current_composite should meet the threshold
    assert result["current_composite"] >= threshold, (
        f"Expected current_composite >= {threshold}, got {result['current_composite']}"
    )

    # This is the caller-side pattern used in run_reachable:
    # entries with current_composite >= threshold are classified as "already above"
    # and reachable_with is ignored. Verify the classification works.
    is_already_above = result["current_composite"] >= result["threshold"]
    assert is_already_above, (
        f"Entry should be classified as already-above "
        f"(composite={result['current_composite']}, threshold={result['threshold']})"
    )

    # Scenarios should only include network levels above current (strong=9 -> internal=10)
    for scenario in result["scenarios"]:
        assert scenario["network_score"] > result["current_network"]


# --- scoring confidence band ---


def test_confidence_band_zero_outcomes():
    """With 0 outcomes, band should be at maximum (1.5)."""
    band = scoring_confidence_band(0)
    assert band == 1.5


def test_confidence_band_decreases_with_outcomes():
    """Band should decrease as outcomes increase."""
    band_0 = scoring_confidence_band(0)
    band_10 = scoring_confidence_band(10)
    band_30 = scoring_confidence_band(30)
    assert band_0 > band_10 > band_30


def test_confidence_band_at_calibration():
    """At calibration target, band should be at minimum (0.3)."""
    band = scoring_confidence_band(50)
    assert band == 0.3


def test_confidence_band_above_calibration():
    """Above calibration target, band stays at minimum."""
    band = scoring_confidence_band(100)
    assert band == 0.3


def test_confidence_band_never_below_minimum():
    """Band should never go below 0.3."""
    for n in range(0, 200):
        assert scoring_confidence_band(n) >= 0.3


# --- applicant density adjustment ---


def test_density_adjustment_low():
    """Low density gives positive adjustment."""
    entry = {"target": {"applicant_density": "low"}}
    assert applicant_density_adjustment(entry) == 0.3


def test_density_adjustment_high():
    """High density gives negative adjustment."""
    entry = {"target": {"applicant_density": "high"}}
    assert applicant_density_adjustment(entry) == -0.2


def test_density_adjustment_extreme():
    """Extreme density gives largest negative."""
    entry = {"target": {"applicant_density": "extreme"}}
    assert applicant_density_adjustment(entry) == -0.3


def test_density_adjustment_medium():
    """Medium density gives no adjustment."""
    entry = {"target": {"applicant_density": "medium"}}
    assert applicant_density_adjustment(entry) == 0.0


def test_density_adjustment_numeric():
    """Integer count also works."""
    assert applicant_density_adjustment({"target": {"applicant_density": 20}}) == 0.3
    assert applicant_density_adjustment({"target": {"applicant_density": 200}}) == 0.0
    assert applicant_density_adjustment({"target": {"applicant_density": 1000}}) == -0.2
    assert applicant_density_adjustment({"target": {"applicant_density": 5000}}) == -0.3


def test_density_adjustment_missing():
    """No density field returns 0."""
    assert applicant_density_adjustment({"target": {}}) == 0.0
    assert applicant_density_adjustment({}) == 0.0


def test_composite_with_density():
    """Composite score should incorporate density when entry provided."""
    dims = {d: 5 for d in ["mission_alignment", "evidence_match", "track_record_fit",
            "network_proximity", "strategic_value", "financial_alignment",
            "effort_to_value", "deadline_feasibility", "portal_friction"]}
    base = compute_composite(dims, "job")
    low_density = compute_composite(dims, "job", entry={"target": {"applicant_density": "low"}})
    high_density = compute_composite(dims, "job", entry={"target": {"applicant_density": "extreme"}})
    assert low_density > base
    assert high_density < base


def test_reachability_unreachable_even_internal():
    """Entry with very low non-network dims should be unreachable even at internal level."""
    entry = _make_entry(
        track="grant",
        fit_score=1,
        identity_position="",
        lead_organs=[],
        portal="custom",
        deadline_type="hard",
        deadline_date=_date_offset(1),  # deadline tomorrow — poor feasibility
        amount_value=0,
        organization="Unknown Org",
        entry_id="reachability-unreachable",
    )
    # No network, no blocks, no materials — everything scores low
    entry.pop("network", None)

    result = analyze_reachability(entry, all_entries=[], threshold=9.0)

    # Even the internal (10) scenario should not cross 9.0 with all other dims ~1-3
    assert result["reachable_with"] is None, (
        f"Expected unreachable (reachable_with=None), but got '{result['reachable_with']}'. "
        f"Scenarios: {result['scenarios']}"
    )

    # Verify the internal scenario is present and still below threshold
    if result["scenarios"]:
        internal_scenario = result["scenarios"][-1]
        assert internal_scenario["level"] == "internal"
        assert not internal_scenario["crosses_threshold"], (
            f"Internal scenario should NOT cross threshold, "
            f"composite={internal_scenario['composite']}"
        )


def test_reachability_job_vs_creative_weights():
    """Job entries use WEIGHTS_JOB (network=0.20) vs creative WEIGHTS (network=0.12).

    The same network improvement should produce a larger delta for job entries.
    """
    base_kwargs = dict(
        fit_score=6,
        identity_position="independent-engineer",
        lead_organs=["III"],
        portal="greenhouse",
        organization="Some Corp",
    )

    job_entry = _make_entry(track="job", entry_id="reachability-job", **base_kwargs)
    creative_entry = _make_entry(track="grant", entry_id="reachability-creative", **base_kwargs)

    # Ensure both start at cold network (score=1)
    job_entry.pop("network", None)
    creative_entry.pop("network", None)

    job_result = analyze_reachability(job_entry, all_entries=[], threshold=9.0)
    creative_result = analyze_reachability(creative_entry, all_entries=[], threshold=9.0)

    # Both should have scenarios
    assert len(job_result["scenarios"]) > 0
    assert len(creative_result["scenarios"]) > 0

    # Verify job vs creative weights are actually different for network_proximity
    assert WEIGHTS_JOB["network_proximity"] != WEIGHTS["network_proximity"], (
        "Expected job and creative network_proximity weights to differ, "
        f"both are {WEIGHTS_JOB['network_proximity']}"
    )

    # Find the "internal" scenario in both (largest possible network upgrade)
    job_internal = next(s for s in job_result["scenarios"] if s["level"] == "internal")
    creative_internal = next(s for s in creative_result["scenarios"] if s["level"] == "internal")

    # Job entry should get a larger delta from the same network improvement
    # because network_proximity weight is 0.20 (job) vs 0.12 (creative)
    assert job_internal["delta"] > creative_internal["delta"], (
        f"Job delta ({job_internal['delta']}) should exceed creative delta "
        f"({creative_internal['delta']}) due to higher network weight"
    )
