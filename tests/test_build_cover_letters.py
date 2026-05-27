"""Direct tests for scripts/build_cover_letters.py markdown conversion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_cover_letters as bcl


def test_md_to_html_body_wraps_paragraphs():
    out = bcl.md_to_html_body("First para.\n\nSecond para.")
    assert "<p>First para.</p>" in out
    assert "<p>Second para.</p>" in out


def test_md_to_html_body_converts_bold_and_italic():
    out = bcl.md_to_html_body("This is **bold** and *italic*.")
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out


def test_md_to_html_body_strips_signoff_and_after():
    out = bcl.md_to_html_body("Body para.\n\nSincerely,\n\nJane Doe")
    assert "Sincerely" not in out
    assert "Jane Doe" not in out


def test_md_to_html_body_drops_horizontal_rule():
    out = bcl.md_to_html_body("Para.\n\n---\n\nNext para.")
    assert "---" not in out
    assert "<p>Next para.</p>" in out
