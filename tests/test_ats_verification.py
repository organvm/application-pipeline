"""Direct tests for scripts/ats_verification.py URL helpers (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ats_verification as av


def test_ashby_slug_from_title():
    assert av._ashby_slug_from_title("Software Engineer, Enterprise Platform") == "software-engineer-enterprise-platform"


def test_ashby_slug_from_title_collapses_separators():
    assert av._ashby_slug_from_title("Data / ML Engineer") == "data-ml-engineer"


def test_ashby_slug_from_url_extracts_id():
    url = "https://jobs.ashbyhq.com/cursor/abc123de-4567"
    assert av._ashby_slug_from_url(url) == "abc123de-4567"


def test_ashby_slug_from_url_none_when_no_match():
    assert av._ashby_slug_from_url("https://example.com/jobs") is None


def test_resolve_application_url_passthrough_for_non_ashby():
    entry = {"target": {
        "organization": "Acme",
        "application_url": "https://acme.com/apply",
        "portal": "greenhouse",
    }}
    assert av.resolve_application_url(entry) == "https://acme.com/apply"


def test_resolve_application_url_empty_for_bad_target():
    assert av.resolve_application_url({"target": "not-a-dict"}) == ""
