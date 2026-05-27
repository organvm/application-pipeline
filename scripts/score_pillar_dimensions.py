"""Pillar-specific dimension scoring for the three-pillar rubric.

Completes the three-pillar refactor (issue #56): these 7 dimensions are
weighted in weights_job / weights_grant / weights_consulting but were
previously never computed (defaulting to 5 in compute_composite, capping
composites and carrying no signal). Each scorer returns an int in [1, 10],
defaulting to a neutral 5 when no signal is available, and supports the
``explain=True`` (value, reason) convention used by the other dimension
modules.

Pillar map:
  Jobs       -> studio_alignment, remote_flexibility
  Grants     -> narrative_fit, prestige_multiplier, cycle_urgency
  Consulting -> recurring_potential, client_fit
"""

from __future__ import annotations

from pipeline_lib import days_until, parse_date
from score_constants import HIGH_PRESTIGE

ScoreResult = int | tuple[int, str]


def _ret(result: int, reason: str, explain: bool) -> ScoreResult:
    result = max(1, min(10, int(round(result))))
    if explain:
        return result, reason
    return result


def _entry_text(entry: dict) -> str:
    """Concatenate the searchable text fields of an entry, lowercased."""
    target = entry.get("target") or {}
    parts = [
        str(entry.get("name") or ""),
        str(target.get("organization") or "") if isinstance(target, dict) else "",
        str(target.get("description") or "") if isinstance(target, dict) else "",
    ]
    tags = entry.get("tags") or []
    if isinstance(tags, list):
        parts.extend(str(t) for t in tags)
    return " ".join(parts).lower()


def _identity_position(entry: dict) -> str:
    fit = entry.get("fit") or {}
    return (fit.get("identity_position") or "") if isinstance(fit, dict) else ""


def _network_strength(entry: dict) -> str:
    network = entry.get("network") or {}
    if isinstance(network, dict):
        return str(network.get("relationship_strength") or "").lower()
    return ""


def _prestige_for_org(org: str) -> tuple[int, str] | None:
    """Return (score, matched_name) if org matches the prestige list."""
    if not org:
        return None
    for name, score in HIGH_PRESTIGE.items():
        if name.lower() in org.lower():
            return score, name
    return None


# ORGANVM studio thesis: AI orchestration, creative technology, systems,
# platform/DevEx, governance. Positions and keywords that advance it.
_STUDIO_POSITIONS = {
    "creative-technologist",
    "systems-artist",
    "platform-orchestrator",
    "independent-engineer",
    "governance-compliance-architect",
    "documentation-engineer",
}
_STUDIO_KEYWORDS = (
    "ai", "ml", "llm", "agent", "creative", "platform", "developer",
    "infrastructure", "research", "orchestrat", "governance", "design system",
    "devrel", "developer experience", "open source", "open-source",
)
_RECURRING_KEYWORDS = (
    "retainer", "ongoing", "recurring", "partnership", "fractional",
    "advisory", "monthly", "ongoing support", "managed",
)
_ONEOFF_KEYWORDS = ("workshop", "one-time", "one off", "one-off", "single")


def score_studio_alignment(entry: dict, explain: bool = False) -> ScoreResult:
    """Jobs pillar: alignment with the ORGANVM studio thesis."""
    score = 5
    parts = ["base 5"]

    position = _identity_position(entry)
    if position in _STUDIO_POSITIONS:
        score += 2
        parts.append(f"position={position} (+2)")

    text = _entry_text(entry)
    kw_hits = sorted({kw for kw in _STUDIO_KEYWORDS if kw in text})
    if kw_hits:
        bonus = min(len(kw_hits), 2)
        score += bonus
        parts.append(f"keywords {kw_hits[:3]} (+{bonus})")

    target = entry.get("target") or {}
    org = (target.get("organization") or "") if isinstance(target, dict) else ""
    prestige = _prestige_for_org(org)
    if prestige and prestige[0] >= 6:
        score += 1
        parts.append(f'org "{prestige[1]}" studio-tier (+1)')

    return _ret(score, " | ".join(parts) + f" = {max(1, min(10, score))}", explain)


def score_remote_flexibility(entry: dict, explain: bool = False) -> ScoreResult:
    """Jobs pillar: how remote-friendly the role is."""
    target = entry.get("target") or {}
    if not isinstance(target, dict):
        return _ret(5, "no target -> neutral 5", explain)

    loc_class = (target.get("location_class") or "").lower()
    location = (target.get("location") or "").lower()

    mapping = {
        "remote-global": (10, "remote-global"),
        "us-remote": (8, "us-remote"),
        "remote-us": (8, "remote-us"),
        "hybrid": (6, "hybrid"),
        "us-onsite": (3, "us-onsite"),
        "onsite": (3, "onsite"),
        "international": (2, "international/onsite"),
    }
    if loc_class in mapping:
        score, label = mapping[loc_class]
        return _ret(score, f"location_class={label} -> {score}", explain)

    # Fall back to the free-text location field.
    if "remote" in location:
        return _ret(8, f'location "{location}" contains remote -> 8', explain)
    if location and "hybrid" in location:
        return _ret(6, f'location "{location}" hybrid -> 6', explain)
    return _ret(5, f"location_class={loc_class or 'unknown'} -> neutral 5", explain)


def score_narrative_fit(entry: dict, explain: bool = False) -> ScoreResult:
    """Grants pillar: fit of the project narrative to the opportunity."""
    score = 4
    parts = ["base 4"]

    submission = entry.get("submission") or {}
    if isinstance(submission, dict):
        blocks = submission.get("blocks_used") or {}
        n_blocks = len(blocks) if isinstance(blocks, (dict, list)) else 0
        # Narrative coverage: up to +3 for a well-composed block set.
        cov = min(n_blocks, 6) / 6 * 3
        if cov:
            score += cov
            parts.append(f"{n_blocks} blocks (+{cov:.1f})")
        variants = submission.get("variant_ids") or {}
        if isinstance(variants, dict) and variants:
            score += 1
            parts.append("cover-letter variant wired (+1)")

    fit = entry.get("fit") or {}
    framing = (fit.get("framing") or "") if isinstance(fit, dict) else ""
    if len(framing) >= 30:
        score += 2
        parts.append(f"framing {len(framing)} chars (+2)")
    elif framing:
        score += 1
        parts.append("short framing (+1)")

    return _ret(score, " | ".join(parts) + f" = {max(1, min(10, int(round(score))))}", explain)


def score_prestige_multiplier(entry: dict, explain: bool = False) -> ScoreResult:
    """Grants pillar: prestige of the funder/opportunity."""
    target = entry.get("target") or {}
    org = (target.get("organization") or "") if isinstance(target, dict) else ""
    prestige = _prestige_for_org(org)
    if prestige:
        score, name = prestige
        return _ret(score, f'org "{org}" matched "{name}" -> {score} (prestige list)', explain)
    # No prestige match: neutral-low (unknown funder reputation).
    return _ret(5, f'org "{org}" not in prestige list -> neutral 5', explain)


def score_cycle_urgency(entry: dict, explain: bool = False) -> ScoreResult:
    """Grants pillar: urgency of the funding cycle (sooner deadline = act now)."""
    deadline = entry.get("deadline") or {}
    if not isinstance(deadline, dict):
        return _ret(3, "no deadline dict -> 3 (low urgency)", explain)

    dtype = deadline.get("type", "")
    date_str = deadline.get("date")
    if dtype in ("rolling", "tba") or not date_str:
        return _ret(3, f"type={dtype or 'no date'} -> 3 (no cycle pressure)", explain)

    deadline_date = parse_date(date_str)
    if not deadline_date:
        return _ret(4, f"unparseable date '{date_str}' -> 4", explain)

    d = days_until(deadline_date)
    if d < 0:
        score = 1
    elif d <= 7:
        score = 9
    elif d <= 14:
        score = 8
    elif d <= 30:
        score = 7
    elif d <= 60:
        score = 5
    else:
        score = 4
    return _ret(score, f"{d}d to deadline -> {score}", explain)


def score_recurring_potential(entry: dict, explain: bool = False) -> ScoreResult:
    """Consulting pillar: potential for recurring (vs one-off) revenue."""
    score = 5
    parts = ["base 5"]

    if entry.get("track") == "consulting":
        score += 1
        parts.append("track=consulting (+1)")

    text = _entry_text(entry)
    rec_hits = sorted({kw for kw in _RECURRING_KEYWORDS if kw in text})
    if rec_hits:
        bonus = min(len(rec_hits) + 1, 3)
        score += bonus
        parts.append(f"recurring signals {rec_hits[:3]} (+{bonus})")

    one_hits = sorted({kw for kw in _ONEOFF_KEYWORDS if kw in text})
    if one_hits:
        score -= 1
        parts.append(f"one-off signals {one_hits[:2]} (-1)")

    return _ret(score, " | ".join(parts) + f" = {max(1, min(10, score))}", explain)


def score_client_fit(entry: dict, explain: bool = False) -> ScoreResult:
    """Consulting pillar: alignment between the client and the studio."""
    score = 5
    parts = ["base 5"]

    strength = _network_strength(entry)
    strength_bonus = {"strong": 2, "warm": 1, "acquaintance": 0, "cold": -1}.get(strength, 0)
    if strength_bonus:
        sign = "+" if strength_bonus > 0 else ""
        score += strength_bonus
        parts.append(f"relationship={strength} ({sign}{strength_bonus})")

    target = entry.get("target") or {}
    org = (target.get("organization") or "") if isinstance(target, dict) else ""
    prestige = _prestige_for_org(org)
    if prestige and prestige[0] >= 6:
        score += 1
        parts.append(f'org "{prestige[1]}" studio-tier (+1)')

    if _identity_position(entry) in _STUDIO_POSITIONS:
        score += 1
        parts.append("studio-aligned position (+1)")

    return _ret(score, " | ".join(parts) + f" = {max(1, min(10, score))}", explain)
