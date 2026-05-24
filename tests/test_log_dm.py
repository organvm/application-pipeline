"""Direct tests for scripts/log_dm.py lookup helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import log_dm


def test_find_contact_substring_case_insensitive():
    contacts = [{"name": "Jane Smith"}, {"name": "Bob Jones"}]
    assert log_dm._find_contact("SMITH", contacts)["name"] == "Jane Smith"


def test_find_contact_not_found():
    assert log_dm._find_contact("nobody", [{"name": "Jane Smith"}]) is None


def test_find_node_substring_case_insensitive():
    nodes = [{"name": "Acme Corp"}, {"name": "Globex"}]
    assert log_dm._find_node("globex", nodes)["name"] == "Globex"


def test_find_node_not_found():
    assert log_dm._find_node("missing", [{"name": "Acme Corp"}]) is None
