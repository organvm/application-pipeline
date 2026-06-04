"""Tests for the Conductor ACP agent surface (scripts/acp_server.py).

Pure dispatch/message helpers are tested unconditionally; the HTTP surface
requires the optional ``web`` extra and otherwise skips.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import acp_server  # noqa: E402


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------
def test_extract_text_concatenates_text_parts():
    messages = [
        {"role": "user", "parts": [{"content_type": "text/plain", "content": "score"}]},
        {"role": "user", "parts": [{"content_type": "text/plain", "content": "demo-2027"}]},
        {"role": "user", "parts": [{"content_type": "application/json", "content": "{}"}]},
    ]
    assert acp_server.extract_text(messages) == "score demo-2027"


def test_dispatch_help_default():
    out = acp_server.dispatch("")
    assert out and out[0]["parts"][0]["content_type"] == "text/plain"
    assert "commands" in out[0]["parts"][0]["content"].lower()


def test_dispatch_summary_includes_json_part():
    out = acp_server.dispatch("summary")
    parts = out[0]["parts"]
    assert any(p["content_type"] == "application/json" for p in parts)


def test_dispatch_score_requires_id():
    out = acp_server.dispatch("score")
    assert "usage" in out[0]["parts"][0]["content"].lower()


def test_dispatch_score_unknown_entry_is_safe():
    out = acp_server.dispatch("score __no-such-entry__")
    # should produce a message, never raise
    assert out and "parts" in out[0]


def test_run_agent_returns_completed_run():
    run = acp_server.run_agent(
        [{"role": "user", "parts": [{"content_type": "text/plain", "content": "summary"}]}]
    )
    assert run["status"] == "completed"
    assert run["agent_name"] == acp_server.AGENT_NAME
    assert run["run_id"] in acp_server._RUNS


# --------------------------------------------------------------------------
# HTTP surface — requires the web extra.
# --------------------------------------------------------------------------
@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    return TestClient(acp_server.create_app())


def test_list_agents(client):
    r = client.get("/agents")
    assert r.status_code == 200
    assert r.json()["agents"][0]["name"] == acp_server.AGENT_NAME


def test_get_agent_manifest(client):
    r = client.get(f"/agents/{acp_server.AGENT_NAME}")
    assert r.status_code == 200
    assert "capabilities" in r.json()["metadata"]


def test_get_unknown_agent_404(client):
    assert client.get("/agents/nope").status_code == 404


def test_create_run_and_fetch(client):
    body = {
        "agent_name": acp_server.AGENT_NAME,
        "input": [{"role": "user", "parts": [{"content_type": "text/plain", "content": "summary"}]}],
    }
    r = client.post("/runs", json=body)
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    fetched = client.get(f"/runs/{run['run_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run["run_id"]
