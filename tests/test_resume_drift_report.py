"""Direct tests for scripts/resume_drift_report.py text helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import resume_drift_report as rdr


def test_strip_tags_removes_html_and_unescapes_entities():
    assert rdr.strip_tags("<p>Hello &amp; <b>world</b></p>") == "Hello & world"


def test_strip_tags_drops_style_blocks():
    assert rdr.strip_tags("<style>p{color:red}</style><p>Visible</p>") == "Visible"


def test_similarity_identical_is_100():
    assert rdr.similarity("abc", "abc") == 100.0


def test_similarity_both_empty_is_100():
    assert rdr.similarity("", "") == 100.0


def test_similarity_one_empty_is_zero():
    assert rdr.similarity("abc", "") == 0.0


def test_full_text_concatenates_known_sections():
    text = rdr.full_text({"profile": "hello", "skills": "world"})
    assert "hello" in text
    assert "world" in text
