"""Tests for Conductor auth/tiers/quota/billing (scripts/conductor_auth.py).

All pure — no FastAPI required — so these run in the default CI job.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import conductor_auth as auth  # noqa: E402


def test_hash_key_is_stable_and_not_plaintext():
    h = auth.hash_key("sk_test_abc")
    assert h == auth.hash_key("sk_test_abc")
    assert "sk_test_abc" not in h
    assert len(h) == 64


def test_resolve_tier_defaults_to_free():
    assert auth.resolve_tier(None).name == "free"
    assert auth.resolve_tier("nonsense").name == "free"
    assert auth.resolve_tier("STUDIO").name == "studio"


def test_tier_write_capability():
    free = auth.Account(id="a", name="A", tier="free")
    pro = auth.Account(id="b", name="B", tier="pro")
    assert free.can_write() is False
    assert pro.can_write() is True


def test_anonymous_honors_legacy_flag():
    anon = auth.Account(id="anonymous", name="Anon", tier="free", anonymous=True)
    assert anon.can_write(legacy_flag=False) is False
    assert anon.can_write(legacy_flag=True) is True
    # non-anonymous free account never writes regardless of the legacy flag
    named = auth.Account(id="x", name="X", tier="free", anonymous=False)
    assert named.can_write(legacy_flag=True) is False


def test_inactive_account_cannot_write():
    acct = auth.Account(id="c", name="C", tier="studio", active=False)
    assert acct.can_write() is False


def test_store_open_mode_returns_anonymous():
    store = auth.AccountStore(auth_required=False)
    account, error = store.resolve_request(None)
    assert error is None
    assert account.anonymous is True
    assert account.tier == "free"


def test_store_required_mode_rejects_missing_key():
    store = auth.AccountStore(auth_required=True)
    account, error = store.resolve_request(None)
    assert account is None
    assert error == "unauthorized"


def test_store_authenticates_valid_key():
    store = auth.AccountStore()
    key = "sk_live_secret"
    store.accounts_by_hash[auth.hash_key(key)] = auth.Account(
        id="acme", name="Acme", tier="studio", api_key_hash=auth.hash_key(key)
    )
    account, error = store.resolve_request(key)
    assert error is None
    assert account.id == "acme"
    assert account.tier == "studio"
    # wrong key in required mode is unauthorized
    store.auth_required = True
    acct2, err2 = store.resolve_request("wrong")
    assert acct2 is None and err2 == "unauthorized"


def test_quota_enforced_per_tier():
    store = auth.AccountStore()
    acct = auth.Account(id="lim", name="Lim", tier="free")  # 30/min
    now = 1000.0
    allowed = sum(1 for _ in range(31) if store._allow_quota(acct, now=now))
    assert allowed == 30  # 31st is blocked within the same window
    # window slides: far-future request is allowed again
    assert store._allow_quota(acct, now=now + 120) is True


def test_quota_unlimited_for_institution():
    store = auth.AccountStore()
    acct = auth.Account(id="big", name="Big", tier="institution")  # 0 == unlimited
    assert all(store._allow_quota(acct, now=1000.0) for _ in range(500))


def test_load_accounts_file_hashes_plaintext(tmp_path):
    f = tmp_path / "accounts.yaml"
    f.write_text(
        "accounts:\n"
        "  - id: acme\n"
        "    name: Acme Studio\n"
        "    tier: studio\n"
        "    api_key: sk_live_xxx\n"
        "  - id: jane\n"
        "    name: Jane\n"
        "    tier: pro\n"
        f"    api_key_hash: {auth.hash_key('sk_pro_jane')}\n"
    )
    store = auth.AccountStore()
    n = store.load_accounts_file(f)
    assert n == 2
    acme, _ = store.resolve_request("sk_live_xxx")
    assert acme.id == "acme" and acme.tier == "studio"
    jane, _ = store.resolve_request("sk_pro_jane")
    assert jane.id == "jane" and jane.tier == "pro"


def test_from_env_reads_flags(monkeypatch, tmp_path):
    monkeypatch.setenv("CONDUCTOR_AUTH_REQUIRED", "1")
    monkeypatch.setenv("CONDUCTOR_ANON_TIER", "pro")
    monkeypatch.delenv("CONDUCTOR_ACCOUNTS_FILE", raising=False)
    store = auth.AccountStore.from_env()
    assert store.auth_required is True
    assert store.anon_tier == "pro"


def test_account_public_view_includes_plan_and_caps():
    acct = auth.Account(id="v", name="V", tier="pro")
    view = auth.account_public_view(acct)
    assert view["tier"] == "pro"
    assert view["can_write"] is True
    assert view["plan"]["price_usd_month"] == auth.PLANS["pro"].monthly_price_usd
    assert "api" in view["surfaces"]


def test_plans_cover_all_tiers():
    assert set(auth.PLANS) == set(auth.TIERS)


def test_billing_reexports_are_available():
    # Backward-compat: billing symbols importable from conductor_auth.
    assert hasattr(auth, "get_billing_provider")
    assert hasattr(auth, "default_registry")
