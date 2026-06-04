"""Tests for the multi-rail billing registry (scripts/conductor_billing.py).

Pure — no FastAPI required — so these run in the default CI job. The point of
this module is *plural points of entry*: never a single payment rail.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import conductor_billing as billing  # noqa: E402


def test_default_registry_has_multiple_rails(monkeypatch):
    monkeypatch.delenv("CONDUCTOR_BILLING_PROVIDERS", raising=False)
    reg = billing.default_registry()
    ids = {p.id for p in reg.providers}
    # Never a single door: at least Stripe + a non-card alternative.
    assert len(reg.providers) >= 3
    assert "stripe" in ids
    assert "github_sponsors" in ids
    assert "invoice" in ids


def test_options_returns_entry_point_per_rail(monkeypatch):
    monkeypatch.delenv("CONDUCTOR_BILLING_PROVIDERS", raising=False)
    reg = billing.default_registry()
    opts = reg.options("acme", "pro", 19)
    assert len(opts) == len(reg.providers)
    for o in opts:
        assert o["tier"] == "pro"
        assert o["price_usd"] == 19
        assert o["url"]
        assert o["provider"] and o["label"]


def test_github_sponsors_is_a_live_link(monkeypatch):
    monkeypatch.setenv("CONDUCTOR_GITHUB_SPONSORS_USER", "4444j99")
    gh = billing.GitHubSponsorsProvider()
    url = gh.checkout_url("acme", "studio")
    assert url == "https://github.com/sponsors/4444j99"
    assert gh.kind == "sponsorship"


def test_invoice_rail_is_card_free_mailto():
    inv = billing.InvoiceProvider()
    url = inv.checkout_url("acme", "institution")
    assert url.startswith("mailto:")
    assert inv.recurring is False
    assert inv.kind == "invoice"


def test_stripe_and_paypal_read_env_links(monkeypatch):
    monkeypatch.setenv("CONDUCTOR_STRIPE_LINK", "https://buy.stripe.com/test")
    monkeypatch.setenv("CONDUCTOR_PAYPAL_LINK", "https://paypal.me/organvm")
    s = billing.StripeProvider().checkout_url("acme", "pro")
    p = billing.PayPalProvider().checkout_url("acme", "pro")
    assert s.startswith("https://buy.stripe.com/test")
    assert "account=acme" in s and "tier=pro" in s
    assert p.startswith("https://paypal.me/organvm")


def test_provider_selection_via_env(monkeypatch):
    monkeypatch.setenv("CONDUCTOR_BILLING_PROVIDERS", "paypal,invoice")
    reg = billing.default_registry()
    assert [p.id for p in reg.providers] == ["paypal", "invoice"]


def test_empty_config_falls_back_to_null(monkeypatch):
    monkeypatch.setenv("CONDUCTOR_BILLING_PROVIDERS", "nonsense,more-nonsense")
    reg = billing.default_registry()
    assert [p.id for p in reg.providers] == ["null"]
    assert isinstance(reg.primary(), billing.NullBillingProvider)


def test_get_billing_provider_compat_shim(monkeypatch):
    monkeypatch.setenv("CONDUCTOR_BILLING_PROVIDERS", "stripe")
    provider = billing.get_billing_provider()
    url = provider.checkout_url("acme", "pro")
    assert "account=acme" in url and "tier=pro" in url
    assert provider.record_usage("acme", 5) is None


def test_billing_provider_alias_is_base_class():
    assert billing.BillingProvider is billing.PaymentProvider
