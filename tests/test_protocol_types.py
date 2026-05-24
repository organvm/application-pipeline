"""Direct tests for scripts/protocol_types.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import protocol_types as pt


def test_agent_from_contact_maps_fields():
    agent = pt.Agent.from_contact({
        "name": "Jane Doe",
        "organization": "Acme",
        "role": "Engineer",
        "relationship_strength": 2.0,
    })
    assert agent.name == "Jane Doe"
    assert agent.organization == "Acme"
    assert agent.role == "Engineer"
    assert agent.relationship_strength == 2.0


def test_agent_from_contact_defaults():
    agent = pt.Agent.from_contact({})
    assert agent.name == ""
    assert agent.pipeline_entries == []
    assert agent.tags == []


def test_message_char_limit_linkedin_pre_boundary():
    msg = pt.Message(text="hi", channel="linkedin", phase="pre_boundary")
    assert msg.char_limit == 300


def test_message_char_limit_post_boundary_is_none():
    msg = pt.Message(text="hi", channel="linkedin", phase="post_boundary")
    assert msg.char_limit is None


def test_message_sentences_splits_on_punctuation():
    msg = pt.Message(text="First sentence. Second one! Third?")
    assert msg.sentences() == ["First sentence.", "Second one!", "Third?"]


def test_claim_is_valid_requires_specificity_and_novelty():
    valid = pt.Claim(text="x", specificity_score=0.5, is_falsifiable=True)
    assert valid.is_valid is True
    no_specificity = pt.Claim(text="x", specificity_score=0.0, is_falsifiable=True)
    assert no_specificity.is_valid is False
    no_novelty = pt.Claim(text="x", specificity_score=0.5, is_falsifiable=False, is_frame_novel=False)
    assert no_novelty.is_valid is False
