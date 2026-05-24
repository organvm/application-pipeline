"""Direct tests for scripts/linkedin_composer.py audit helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import linkedin_composer as lc


def test_audit_char_count_fail_when_over_limit():
    result = lc.audit_char_count("x" * (lc.MAX_CHARS + 1))
    assert result["grade"] == "FAIL"
    assert result["article"] == "FORM"


def test_audit_char_count_pass_in_ideal_range():
    text = "word " * 240  # 1200 chars, within IDEAL_MIN..IDEAL_MAX
    assert lc.IDEAL_MIN <= len(text) <= lc.IDEAL_MAX
    assert lc.audit_char_count(text)["grade"] == "PASS"


def test_run_full_audit_returns_all_checks():
    results = lc.run_full_audit("Some post text about governance systems.")
    assert len(results) == 8
    assert all("grade" in r and r["grade"] in {"PASS", "WEAK", "FAIL"} for r in results)
