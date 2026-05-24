"""Tests for scripts/pipeline_freshness.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_freshness
from pipeline_freshness import (
    compute_freshness_score,
    flush_stale_active_jobs,
    get_entry_era,
    get_freshness_tier,
    get_posting_age_hours,
)


@pytest.fixture(autouse=True)
def _allow_mutation(monkeypatch):
    """This module exercises real flush behavior on tmp dirs, so disable the
    global PIPELINE_NO_MUTATE guard set in conftest (which would no-op flush)."""
    monkeypatch.delenv("PIPELINE_NO_MUTATE", raising=False)


def test_get_entry_era_volume_and_precision():
    assert get_entry_era({"timeline": {"submitted": "2026-03-03"}}) == "volume"
    assert get_entry_era({"timeline": {"submitted": "2026-03-04"}}) == "precision"


def test_get_posting_age_hours_date_only():
    entry = {"timeline": {"posting_date": (date.today() - timedelta(days=2)).isoformat()}}
    assert get_posting_age_hours(entry) == 48.0


def test_get_freshness_tier_non_job_returns_none():
    assert get_freshness_tier({"track": "grant", "timeline": {"posting_date": date.today().isoformat()}}) is None


def test_compute_freshness_score_stale_clamps_to_zero():
    entry = {
        "track": "job",
        "timeline": {"posting_date": (date.today() - timedelta(days=10)).isoformat()},
    }
    assert compute_freshness_score(entry) == 0.0


def test_get_freshness_tier_respects_custom_thresholds(monkeypatch):
    monkeypatch.setattr(
        pipeline_freshness,
        "load_market_intelligence",
        lambda: {"job_posting_freshness_hours": {"fresh": 1, "warm": 2, "stale": 3}},
    )
    entry = {"track": "job", "timeline": {"posting_date": date.today().isoformat()}}
    assert get_freshness_tier(entry) == "hot"


def test_flush_stale_active_jobs_moves_old_job_entries(tmp_path, monkeypatch):
    """Stale job entries (>72h) in active/ are moved to research_pool/."""
    import yaml

    active = tmp_path / "pipeline" / "active"
    pool = tmp_path / "pipeline" / "research_pool"
    active.mkdir(parents=True)
    pool.mkdir(parents=True)

    # Stale job entry (10 days old)
    stale_entry = {
        "id": "stale-job",
        "track": "job",
        "status": "qualified",
        "timeline": {"date_added": (date.today() - timedelta(days=10)).isoformat()},
    }
    (active / "stale-job.yaml").write_text(yaml.dump(stale_entry))

    # Fresh job entry (1 day old)
    fresh_entry = {
        "id": "fresh-job",
        "track": "job",
        "status": "qualified",
        "timeline": {"date_added": date.today().isoformat()},
    }
    (active / "fresh-job.yaml").write_text(yaml.dump(fresh_entry))

    # Grant entry (old but exempt)
    grant_entry = {
        "id": "old-grant",
        "track": "grant",
        "status": "qualified",
        "timeline": {"date_added": (date.today() - timedelta(days=30)).isoformat()},
    }
    (active / "old-grant.yaml").write_text(yaml.dump(grant_entry))

    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_ACTIVE", active)
    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_RESEARCH_POOL", pool)

    flushed = flush_stale_active_jobs(quiet=True)

    assert flushed == 1
    assert not (active / "stale-job.yaml").exists()
    assert (pool / "stale-job.yaml").exists()
    assert (active / "fresh-job.yaml").exists()
    assert (active / "old-grant.yaml").exists()


def test_flush_stale_active_jobs_removes_duplicates(tmp_path, monkeypatch):
    """If entry already exists in research_pool/, just delete from active/."""
    import yaml

    active = tmp_path / "pipeline" / "active"
    pool = tmp_path / "pipeline" / "research_pool"
    active.mkdir(parents=True)
    pool.mkdir(parents=True)

    entry = {
        "id": "dup-job",
        "track": "job",
        "status": "qualified",
        "timeline": {"date_added": (date.today() - timedelta(days=5)).isoformat()},
    }
    (active / "dup-job.yaml").write_text(yaml.dump(entry))
    (pool / "dup-job.yaml").write_text(yaml.dump(entry))

    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_ACTIVE", active)
    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_RESEARCH_POOL", pool)

    flushed = flush_stale_active_jobs(quiet=True)

    assert flushed == 1
    assert not (active / "dup-job.yaml").exists()
    assert (pool / "dup-job.yaml").exists()


def test_flush_stale_exempts_all_deadline_tracks(tmp_path, monkeypatch):
    """All deadline-based tracks (grant, residency, fellowship, creative, writing) are exempt."""
    import yaml

    active = tmp_path / "pipeline" / "active"
    pool = tmp_path / "pipeline" / "research_pool"
    active.mkdir(parents=True)
    pool.mkdir(parents=True)

    for track in ("grant", "residency", "fellowship", "creative", "writing"):
        entry = {
            "id": f"old-{track}",
            "track": track,
            "status": "qualified",
            "timeline": {"date_added": (date.today() - timedelta(days=30)).isoformat()},
        }
        (active / f"old-{track}.yaml").write_text(yaml.dump(entry))

    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_ACTIVE", active)
    monkeypatch.setattr(pipeline_freshness, "PIPELINE_DIR_RESEARCH_POOL", pool)

    flushed = flush_stale_active_jobs(quiet=True)

    assert flushed == 0
    assert len(list(active.glob("*.yaml"))) == 5
