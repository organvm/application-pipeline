"""Direct tests for scripts/reconcile_outreach.py pure helpers."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import reconcile_outreach as ro


def test_parse_date_month_day_uses_reference_year():
    assert ro._parse_date("Mar 23", reference_year=2026) == "2026-03-23"


def test_parse_date_with_explicit_year():
    assert ro._parse_date("Dec 27, 2025") == "2025-12-27"


def test_parse_date_time_only_is_today():
    assert ro._parse_date("8:03 PM") == str(date.today())


def test_extract_contact_returns_other_party_owner_first():
    line = "Open the options list in your conversation with Anthony Padavano and Jane Smith"
    assert ro._extract_contact_from_options_line(line, owner="Anthony Padavano") == "Jane Smith"


def test_extract_contact_returns_other_party_owner_second():
    line = "Open the options list in your conversation with Jane Smith and Anthony Padavano"
    assert ro._extract_contact_from_options_line(line, owner="Anthony Padavano") == "Jane Smith"


def test_extract_contact_no_match_returns_none():
    assert ro._extract_contact_from_options_line("some unrelated line", owner="X") is None


def test_find_contact_substring_case_insensitive():
    contacts = [{"name": "Jane Smith"}, {"name": "Bob Jones"}]
    assert ro._find_contact("jane", contacts)["name"] == "Jane Smith"


def test_find_contact_not_found():
    assert ro._find_contact("nobody", [{"name": "Jane Smith"}]) is None
