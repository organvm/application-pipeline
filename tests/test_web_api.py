"""Tests for the Conductor REST API + dashboard backend (scripts/web_api.py).

The FastAPI app and TestClient require the optional ``web`` extra
(``pip install -e ".[web]"``). When it is absent (e.g. the default CI job),
these tests skip — but the module's pure helpers are tested unconditionally.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import web_api  # noqa: E402


# --------------------------------------------------------------------------
# Pure helpers — no FastAPI needed.
# --------------------------------------------------------------------------
def test_to_jsonable_handles_enum_and_dataclass():
    import pipeline_api as api

    result = api.ScoreResult(status=api.ResultStatus.DRY_RUN, entry_id="x", new_score=8.0)
    out = web_api.to_jsonable(result)
    assert out["status"] == "dry_run"  # enum -> value
    assert out["entry_id"] == "x"
    assert out["new_score"] == 8.0


def test_to_jsonable_nested_and_paths():
    payload = {"p": Path("/tmp/x"), "items": [api_status() for _ in range(2)]}
    out = web_api.to_jsonable(payload)
    assert out["p"] == "/tmp/x"
    assert out["items"] == ["success", "success"]


def api_status():
    import pipeline_api as api

    return api.ResultStatus.SUCCESS


def test_entry_summary_projects_schema_fields():
    entry = {
        "id": "demo-2027",
        "name": "Demo Grant 2027",
        "track": "grant",
        "status": "staged",
        "target": {"organization": "Demo Org", "application_url": "https://x"},
        "deadline": {"date": "2027-01-01", "type": "hard"},
        "fit": {"score": 8.5, "identity_position": "systems-artist"},
    }
    s = web_api.entry_summary(entry)
    assert s["id"] == "demo-2027"
    assert s["organization"] == "Demo Org"
    assert s["score"] == 8.5
    assert s["deadline"] == "2027-01-01"
    assert s["identity_position"] == "systems-artist"


def test_writes_allowed_env(monkeypatch):
    monkeypatch.delenv("CONDUCTOR_ALLOW_WRITES", raising=False)
    assert web_api.writes_allowed() is False
    monkeypatch.setenv("CONDUCTOR_ALLOW_WRITES", "1")
    assert web_api.writes_allowed() is True


def test_pipeline_summary_shape():
    # Runs against the live repo pipeline data; only assert structural contract.
    summary = web_api.pipeline_summary()
    assert set(summary) >= {"total", "actionable", "submitted", "by_status", "by_track", "writes_allowed"}
    assert isinstance(summary["by_status"], dict)
    assert summary["total"] >= 0


# --------------------------------------------------------------------------
# HTTP surface — requires the web extra.
# --------------------------------------------------------------------------
@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    return TestClient(web_api.create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "conductor"


def test_summary_endpoint(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    assert "by_status" in r.json()


def test_entries_endpoint_returns_list(client):
    r = client.get("/api/entries")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_entry_not_found(client):
    r = client.get("/api/entries/__does-not-exist__")
    assert r.status_code == 404


def test_precedents_endpoint_structure(client):
    r = client.get("/api/precedents")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["version"] is not None
    # Three named precedent processes.
    assert set(body["precedents"]) == {"application_genesis", "evaluative_authority", "standards"}
    # Four boundary conditions.
    assert len(body["boundary_conditions"]) == 4
    # All domains present; the single demonstrated instance is reported honestly.
    assert set(body["domains"]) == {"academic", "market", "engineering"}
    assert body["domains"]["academic"]["sgo"]["validation_status"] == "demonstrated"


def test_precedents_endpoint_domain_filter(client):
    r = client.get("/api/precedents?domain=market")
    assert r.status_code == 200
    body = r.json()
    assert set(body["domains"]) == {"market"}
    assert "hiring_employer_side" in body["domains"]["market"]


def test_precedents_endpoint_unknown_domain(client):
    r = client.get("/api/precedents?domain=__nope__")
    assert r.status_code == 404


def test_score_endpoint_is_dry_run_without_writes(client, monkeypatch):
    monkeypatch.delenv("CONDUCTOR_ALLOW_WRITES", raising=False)
    r = client.post("/api/entries/__nope__/score")
    assert r.status_code == 200
    body = r.json()
    # unknown entry -> error status, but never a real write
    assert body["status"] in {"error", "dry_run"}


def test_openapi_docs_available(client):
    assert client.get("/openapi.json").status_code == 200


def test_account_endpoint_open_mode(client):
    r = client.get("/api/account")
    assert r.status_code == 200
    body = r.json()
    assert body["anonymous"] is True
    assert body["tier"] == "free"
    assert "checkout_url" in body
    # plural points of entry — more than one payment rail is always offered
    assert isinstance(body["billing_options"], list)
    assert len(body["billing_options"]) >= 2
    providers = {o["provider"] for o in body["billing_options"]}
    assert "github_sponsors" in providers  # a non-card door always exists


def test_billing_plans_endpoint(client):
    r = client.get("/api/billing/plans")
    assert r.status_code == 200
    tiers = {p["tier"] for p in r.json()}
    assert {"free", "pro", "studio", "institution"} <= tiers


def test_billing_options_endpoint_lists_rails(client):
    r = client.get("/api/billing/options?tier=studio")
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "studio"
    assert len(body["rails"]) >= 2
    assert all(rail["tier"] == "studio" for rail in body["rails"])


def test_auth_required_rejects_unauthenticated(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CONDUCTOR_AUTH_REQUIRED", "1")
    monkeypatch.delenv("CONDUCTOR_ACCOUNTS_FILE", raising=False)
    c = TestClient(web_api.create_app())
    # protected (write/account) routes require a key
    assert c.post("/api/entries/x/score").status_code == 401
    assert c.get("/api/account").status_code == 401
    # open read routes still work (no dependency)
    assert c.get("/api/summary").status_code == 200


def test_valid_pro_key_authorizes_writes(monkeypatch, tmp_path):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(
        "accounts:\n  - id: pro1\n    name: Pro One\n    tier: pro\n    api_key: sk_pro_1\n"
    )
    monkeypatch.setenv("CONDUCTOR_AUTH_REQUIRED", "1")
    monkeypatch.setenv("CONDUCTOR_ACCOUNTS_FILE", str(accounts))
    c = TestClient(web_api.create_app())
    headers = {"X-API-Key": "sk_pro_1"}
    acct = c.get("/api/account", headers=headers)
    assert acct.status_code == 200
    assert acct.json()["tier"] == "pro" and acct.json()["can_write"] is True
    # authorized write call returns 200 (engine may still report a not-found error)
    assert c.post("/api/entries/__nope__/score", headers=headers).status_code == 200
