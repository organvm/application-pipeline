"""Direct tests for scripts/apply.py pure helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import apply


def test_extract_board_and_job_standard_url():
    entry = {"target": {"application_url": "https://boards.greenhouse.io/acme/jobs/12345"}}
    assert apply._extract_board_and_job(entry) == ("acme", "12345")


def test_extract_board_and_job_gh_jid_param():
    entry = {"target": {"application_url": "https://boards.greenhouse.io/acme/jobs?gh_jid=67890"}}
    assert apply._extract_board_and_job(entry) == ("acme", "67890")


def test_extract_board_and_job_none_for_non_greenhouse():
    entry = {"target": {"application_url": "https://example.com/careers"}}
    assert apply._extract_board_and_job(entry) is None


def test_check_overlap_detects_shared_four_word_phrase():
    cover_letter = "we build production grade creative instruments daily"
    resume_html = "<p>we build production grade creative instruments</p>"
    overlaps = apply._check_overlap(cover_letter, resume_html)
    assert overlaps  # shares 4-word phrases
    assert all(len(p) > 15 for p in overlaps)


def test_check_overlap_empty_when_no_shared_phrase():
    assert apply._check_overlap("totally different words here now", "<p>nothing in common at all</p>") == []
