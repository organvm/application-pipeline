"""Direct tests for scripts/dm_composer.py pure helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import dm_composer


def test_compress_hook_matches_known_frame():
    assert dm_composer._compress_hook("I love the promotion state machine design") == "promotion state machine"


def test_compress_hook_truncates_long_text():
    assert dm_composer._compress_hook("one two three four five six seven eight") == "one two three four five six..."


def test_compress_hook_short_text_unchanged():
    assert dm_composer._compress_hook("short phrase") == "short phrase"
