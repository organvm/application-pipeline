"""Direct tests for scripts/protocol_validator.py pure helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import protocol_validator as pv
from protocol_types import Message


def test_specificity_scores_numbers():
    assert pv._specificity("We shipped 2,349 tests last quarter") >= 0.4


def test_specificity_plain_text_is_zero():
    assert pv._specificity("just some plain lowercase words") == 0.0


def test_extract_claims_skips_short_segments_and_scores_specific():
    msg = Message(text="Short. We built a promotion state machine with 103 repos.")
    claims = pv.extract_claims(msg)
    assert all(len(c.text) >= 10 for c in claims)
    assert any(c.specificity_score > 0 for c in claims)


def test_self_description_ratio_all_self_referential():
    msg = Message(text="I built this. My work is here.")
    assert pv.compute_self_description_ratio(msg) == 1.0


def test_self_description_ratio_none():
    msg = Message(text="The system runs. Birds fly south.")
    assert pv.compute_self_description_ratio(msg) == 0.0


def test_self_description_ratio_empty_message():
    assert pv.compute_self_description_ratio(Message(text="")) == 0.0


def test_extract_questions_substantive():
    msg = Message(text="How do you handle correctness guarantees in production systems?")
    questions = pv.extract_questions(msg)
    assert len(questions) == 1
    assert questions[0].is_substantive is True


def test_is_closed_true_for_statement_without_question():
    assert pv.is_closed(Message(text="The system is complete.")) is True


def test_is_closed_false_when_question_present():
    assert pv.is_closed(Message(text="What do you think about this approach?")) is False
