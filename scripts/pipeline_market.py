"""Market and HTTP utility helpers extracted from pipeline_lib."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path


def http_request_with_retry(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> bytes | None:
    """Make an HTTP request with exponential backoff retry."""
    import time
    import urllib.error
    import urllib.request

    headers = headers or {}
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                import sys

                print(
                    f"  HTTP {method} {url} failed after {max_retries} attempts: {exc}",
                    file=sys.stderr,
                )
                return None
    return None


# Required top-level keys in market-intelligence JSON.
# Missing keys are logged as warnings but don't block loading.
MARKET_INTEL_REQUIRED_KEYS = {
    "meta",
    "market_conditions",
    "track_benchmarks",
    "portal_friction_scores",
    "follow_up_protocol",
    "stale_thresholds_days",
}


def _validate_market_intel(data: dict, filepath: Path) -> list[str]:
    """Validate market intelligence JSON structure. Returns list of warnings."""
    import sys

    warnings = []
    missing = MARKET_INTEL_REQUIRED_KEYS - set(data.keys())
    if missing:
        warnings.append(f"market-intelligence: missing required keys: {sorted(missing)}")

    # Validate meta section
    meta = data.get("meta", {})
    if isinstance(meta, dict):
        if not meta.get("sources_count"):
            warnings.append("market-intelligence: meta.sources_count missing")
        if not meta.get("review_by"):
            warnings.append("market-intelligence: meta.review_by missing")

    # Validate portal_friction_scores values are ints 1-10 (skip metadata keys)
    pfs = data.get("portal_friction_scores", {})
    _PFS_META_KEYS = {"source", "note", "description", "updated"}
    if isinstance(pfs, dict):
        for portal, score in pfs.items():
            if portal in _PFS_META_KEYS:
                continue
            if not isinstance(score, int) or not 1 <= score <= 10:
                warnings.append(f"market-intelligence: portal_friction_scores.{portal} invalid: {score}")

    for w in warnings:
        print(f"  WARNING: {w}", file=sys.stderr)
    return warnings


def build_market_intelligence_loader(
    repo_root: Path,
) -> tuple[Callable[[], dict], Callable[[], dict], Callable[[], dict], dict[str, int], dict[str, int]]:
    """Return lazy market-intelligence accessors bound to a repo root."""
    intel_file = repo_root / "strategy" / "market-intelligence-2026.json"
    cache: dict | None = None

    portal_scores_default = {
        "email": 9,
        "custom": 6,
        "web": 6,
        "submittable": 5,
        "greenhouse": 5,
        "lever": 5,
        "ashby": 5,
        "workable": 5,
        "slideroom": 4,
    }

    strategic_base_default = {
        "grant": 7,
        "prize": 8,
        "fellowship": 7,
        "residency": 6,
        "program": 5,
        "writing": 5,
        "emergency": 3,
        "job": 6,
        "consulting": 3,
        "academic": 7,
    }

    def load_market_intelligence() -> dict:
        """Load market-intelligence JSON once, return {} on failure.

        Validates required keys on first load and logs warnings for
        any structural issues (missing keys, invalid values).
        """
        nonlocal cache
        if cache is not None:
            return cache
        if intel_file.exists():
            try:
                with open(intel_file) as f:
                    cache = json.load(f)
                _validate_market_intel(cache, intel_file)
            except (OSError, json.JSONDecodeError):
                cache = {}
        else:
            cache = {}
        return cache

    def get_portal_scores() -> dict:
        """Load portal friction scores from market intel or fallback defaults."""
        intel = load_market_intelligence()
        scores = intel.get("portal_friction_scores", {})
        result = {k: v for k, v in scores.items() if isinstance(v, int)}
        return result if result else portal_scores_default

    def get_strategic_base() -> dict:
        """Load strategic base values derived from acceptance-rate benchmarks."""
        intel = load_market_intelligence()
        benchmarks = intel.get("track_benchmarks", {})
        if not benchmarks:
            return strategic_base_default

        result = {}
        for track, data in benchmarks.items():
            rate = data.get("acceptance_rate") or data.get("cold_response_rate")
            if rate is None:
                result[track] = strategic_base_default.get(track, 5)
            elif rate <= 0.02:
                result[track] = 8
            elif rate <= 0.04:
                result[track] = 7
            elif rate <= 0.06:
                result[track] = 6
            elif rate <= 0.10:
                result[track] = 5
            else:
                result[track] = 4
        return result

    return (
        load_market_intelligence,
        get_portal_scores,
        get_strategic_base,
        portal_scores_default,
        strategic_base_default,
    )


def check_market_intel_freshness(repo_root: Path) -> dict:
    """Check modification time of market-intelligence-2026.json.

    Returns:
        {"fresh": bool, "age_days": float, "warning": str|None}
        Warns if >90 days old, critical if >180 days old.
    """
    import time

    intel_file = repo_root / "strategy" / "market-intelligence-2026.json"
    if not intel_file.exists():
        return {"fresh": False, "age_days": -1, "warning": "market-intelligence-2026.json not found"}

    mtime = intel_file.stat().st_mtime
    age_days = (time.time() - mtime) / 86400

    if age_days > 180:
        return {"fresh": False, "age_days": age_days, "warning": f"CRITICAL: market intel is {age_days:.0f}d old (>180d) — data is unreliable"}
    if age_days > 90:
        return {"fresh": False, "age_days": age_days, "warning": f"WARNING: market intel is {age_days:.0f}d old (>90d) — schedule refresh"}
    return {"fresh": True, "age_days": age_days, "warning": None}

