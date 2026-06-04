#!/usr/bin/env python3
"""Conductor — multi-rail billing registry (plural points of entry).

A product must never depend on a single payment rail. Not everyone has (or
wants) Stripe; some pay via PayPal, some sponsor on GitHub, institutions need an
invoice. So billing here is two independent axes:

  1. **Tiers** (free / pro / studio / institution)  — defined in conductor_auth
  2. **Rails** (stripe / paypal / github_sponsors / invoice / ...) — defined here

For any paid tier we surface *every enabled rail* as a distinct entry point, so a
customer who can't use one door always has another. Adding a rail is adding a
``PaymentProvider`` subclass + an entry in ``CONDUCTOR_BILLING_PROVIDERS`` — no
change to the surfaces that consume it.

This is a *seam*: providers return real, configurable entry-point URLs
(GitHub Sponsors is a live link; others read from env). No card is charged here;
fulfilment/webhooks attach behind each provider.

Env configuration:
  CONDUCTOR_BILLING_PROVIDERS    comma list (default: stripe,paypal,github_sponsors,invoice)
  CONDUCTOR_STRIPE_LINK          base Stripe payment/checkout link
  CONDUCTOR_PAYPAL_LINK          PayPal.me / hosted-button base
  CONDUCTOR_GITHUB_SPONSORS_USER GitHub Sponsors handle (default: 4444j99)
  CONDUCTOR_BILLING_EMAIL        address for invoice requests
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class PaymentEntryPoint:
    """One concrete way to pay for one tier via one rail."""

    provider: str
    label: str
    kind: str  # "subscription" | "one_time" | "sponsorship" | "invoice"
    recurring: bool
    url: str
    tier: str
    price_usd: int
    description: str


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------
class PaymentProvider:
    """Base rail. Subclasses build a tier-specific entry point."""

    id: str = "base"
    label: str = "Base"
    kind: str = "subscription"
    recurring: bool = True

    def checkout_url(self, account_id: str, tier: str) -> str:
        raise NotImplementedError

    def description(self, tier: str, price: int) -> str:
        return f"Pay for {tier} via {self.label}"

    def record_usage(self, account_id: str, units: int) -> None:
        """Usage-metering hook (no-op until a real integration is wired)."""

        return None

    def entry_point(self, account_id: str, tier: str, price: int) -> PaymentEntryPoint:
        return PaymentEntryPoint(
            provider=self.id,
            label=self.label,
            kind=self.kind,
            recurring=self.recurring,
            url=self.checkout_url(account_id, tier),
            tier=tier,
            price_usd=price,
            description=self.description(tier, price),
        )


def _with_params(base: str, **params: str) -> str:
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(params)}"


class StripeProvider(PaymentProvider):
    id = "stripe"
    label = "Stripe"

    def __init__(self) -> None:
        self.base = os.environ.get("CONDUCTOR_STRIPE_LINK", "about:blank#stripe-checkout")

    def checkout_url(self, account_id: str, tier: str) -> str:
        return _with_params(self.base, account=account_id, tier=tier)


class PayPalProvider(PaymentProvider):
    id = "paypal"
    label = "PayPal"

    def __init__(self) -> None:
        self.base = os.environ.get("CONDUCTOR_PAYPAL_LINK", "about:blank#paypal")

    def checkout_url(self, account_id: str, tier: str) -> str:
        return _with_params(self.base, account=account_id, tier=tier)


class GitHubSponsorsProvider(PaymentProvider):
    id = "github_sponsors"
    label = "GitHub Sponsors"
    kind = "sponsorship"

    def __init__(self) -> None:
        self.user = os.environ.get("CONDUCTOR_GITHUB_SPONSORS_USER", "4444j99")

    def checkout_url(self, account_id: str, tier: str) -> str:
        # GitHub Sponsors is a live rail; tier maps to a sponsorship amount on the page.
        return f"https://github.com/sponsors/{self.user}"

    def description(self, tier: str, price: int) -> str:
        return f"Sponsor on GitHub (recurring) — {self.label} supports {tier} access"


class InvoiceProvider(PaymentProvider):
    id = "invoice"
    label = "Invoice / Purchase Order"
    kind = "invoice"
    recurring = False

    def __init__(self) -> None:
        self.email = os.environ.get("CONDUCTOR_BILLING_EMAIL", "billing@organvm.studio")

    def checkout_url(self, account_id: str, tier: str) -> str:
        subject = quote(f"Conductor {tier} — invoice request ({account_id})")
        body = quote(f"Please invoice account '{account_id}' for the Conductor {tier} plan.")
        return f"mailto:{self.email}?subject={subject}&body={body}"

    def description(self, tier: str, price: int) -> str:
        return f"Request an invoice / PO for {tier} (institutions, no card required)"


class NullBillingProvider(PaymentProvider):
    """No-op fallback used when no rails are configured."""

    id = "null"
    label = "Unconfigured"

    def checkout_url(self, account_id: str, tier: str) -> str:
        return _with_params("about:blank#checkout", account=account_id, tier=tier)


_PROVIDER_CLASSES: dict[str, type[PaymentProvider]] = {
    "stripe": StripeProvider,
    "paypal": PayPalProvider,
    "github_sponsors": GitHubSponsorsProvider,
    "invoice": InvoiceProvider,
    "null": NullBillingProvider,
}

DEFAULT_PROVIDER_IDS = ["stripe", "paypal", "github_sponsors", "invoice"]


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
@dataclass
class BillingRegistry:
    """Holds the enabled payment rails and surfaces entry points per tier."""

    providers: list[PaymentProvider]

    def options(self, account_id: str, tier: str, price: int) -> list[dict]:
        """All enabled rails as entry points for one tier (JSON-safe dicts)."""

        return [vars(p.entry_point(account_id, tier, price)) for p in self.providers]

    def primary(self) -> PaymentProvider:
        return self.providers[0] if self.providers else NullBillingProvider()

    @classmethod
    def from_env(cls) -> BillingRegistry:
        raw = os.environ.get("CONDUCTOR_BILLING_PROVIDERS", "").strip()
        ids = [p.strip() for p in raw.split(",") if p.strip()] if raw else list(DEFAULT_PROVIDER_IDS)
        providers: list[PaymentProvider] = []
        for pid in ids:
            cls_ = _PROVIDER_CLASSES.get(pid)
            if cls_:
                providers.append(cls_())
        if not providers:
            providers.append(NullBillingProvider())
        return cls(providers=providers)


def default_registry() -> BillingRegistry:
    return BillingRegistry.from_env()


# Backward-compatible alias kept for callers importing from conductor_auth.
BillingProvider = PaymentProvider


def get_billing_provider() -> PaymentProvider:
    """Return the primary configured rail (compat shim for the older single-rail API)."""

    return default_registry().primary()
