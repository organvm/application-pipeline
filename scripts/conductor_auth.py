#!/usr/bin/env python3
"""Conductor — authentication, tiers, quota, and the billing seam.

This module closes the biggest "honest gap" from the productization build: it
replaces the single global ``CONDUCTOR_ALLOW_WRITES`` flag with per-account
authentication and tier-based capabilities, so writes are gated by *who* is
calling and *what plan* they are on — the foundation for charging money.

Shared by every product surface (REST API, ACP). Dependency-light: API keys are
hashed with stdlib ``hashlib``/``hmac``; accounts load from a YAML file.

Design principles
-----------------
- **Backward compatible.** With no accounts file and ``CONDUCTOR_AUTH_REQUIRED``
  unset, the store runs in *open mode*: every request resolves to an anonymous
  ``free`` account whose write capability still honors the legacy
  ``CONDUCTOR_ALLOW_WRITES`` flag. Existing behavior and tests are preserved.
- **Auth is a seam, billing is a seam.** Real charging needs a provider (Stripe)
  and secrets we do not wire here; instead we model plans + a ``BillingProvider``
  protocol with a null implementation and a documented integration point.

Honest scope
------------
This is per-account *auth + capability + quota*, not per-account *data
isolation*: the pipeline data layer (``pipeline_lib``) still reads one shared
set of YAML directories. True multi-tenant data partitioning (per-account
PIPELINE_ROOT) is the next gap and is called out in the productization spec.

Accounts file format (``CONDUCTOR_ACCOUNTS_FILE``, YAML):

    accounts:
      - id: acme
        name: Acme Studio
        tier: studio
        api_key: sk_live_xxx        # plaintext (dev) — hashed on load
      - id: jdoe
        name: Jane Doe
        tier: pro
        api_key_hash: 9f86d0818...  # sha256 hex (prod)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

try:  # core dep, but keep import resilient
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


# --------------------------------------------------------------------------
# Tiers & plans
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Tier:
    """A capability profile. Surfaces and limits are derived from the plan."""

    name: str
    can_write: bool
    rate_limit_per_min: int  # 0 == unlimited
    surfaces: frozenset[str]


TIERS: dict[str, Tier] = {
    "free": Tier("free", can_write=False, rate_limit_per_min=30, surfaces=frozenset({"dashboard", "api", "mcp"})),
    "pro": Tier("pro", can_write=True, rate_limit_per_min=120, surfaces=frozenset({"dashboard", "api", "mcp"})),
    "studio": Tier(
        "studio", can_write=True, rate_limit_per_min=600, surfaces=frozenset({"dashboard", "api", "mcp", "acp"})
    ),
    "institution": Tier(
        "institution", can_write=True, rate_limit_per_min=0, surfaces=frozenset({"dashboard", "api", "mcp", "acp"})
    ),
}


@dataclass(frozen=True)
class Plan:
    """Billing plan attached to a tier. Prices are hypotheses for discovery."""

    tier: str
    monthly_price_usd: int
    description: str


PLANS: dict[str, Plan] = {
    "free": Plan("free", 0, "Read-only dashboard, 1 track, manual scoring"),
    "pro": Plan("pro", 19, "Writes enabled, all 9 dimensions, MCP access"),
    "studio": Plan("studio", 49, "API + ACP, unlimited tracks, IRA audits, analytics"),
    "institution": Plan("institution", 0, "Custom — vertical editions & licensing"),
}


def resolve_tier(name: str | None) -> Tier:
    """Return the Tier for a name, defaulting to free for unknown/missing names."""

    return TIERS.get((name or "free").lower(), TIERS["free"])


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
def hash_key(api_key: str) -> str:
    """SHA-256 hex digest of an API key (what we store; never the plaintext)."""

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


@dataclass
class Account:
    """An authenticated tenant of the product."""

    id: str
    name: str
    tier: str = "free"
    api_key_hash: str | None = None
    active: bool = True
    anonymous: bool = False

    @property
    def tier_profile(self) -> Tier:
        return resolve_tier(self.tier)

    def can_write(self, *, legacy_flag: bool = False) -> bool:
        """Whether this account may persist state-machine actions.

        Anonymous accounts additionally honor the legacy ``CONDUCTOR_ALLOW_WRITES``
        flag so single-user/dev deployments work without an accounts file.
        """

        if not self.active:
            return False
        if self.tier_profile.can_write:
            return True
        return self.anonymous and legacy_flag

    def plan(self) -> Plan:
        return PLANS.get(self.tier, PLANS["free"])


def _legacy_writes_flag() -> bool:
    return os.environ.get("CONDUCTOR_ALLOW_WRITES", "").strip() in {"1", "true", "yes"}


# --------------------------------------------------------------------------
# Account store (auth + quota)
# --------------------------------------------------------------------------
@dataclass
class AccountStore:
    """Holds accounts, resolves API keys, and enforces per-account quota."""

    accounts_by_hash: dict[str, Account] = field(default_factory=dict)
    auth_required: bool = False
    anon_tier: str = "free"
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    # ---- resolution -----------------------------------------------------
    def _anonymous(self) -> Account:
        return Account(id="anonymous", name="Anonymous", tier=self.anon_tier, anonymous=True)

    def authenticate(self, api_key: str | None) -> Account | None:
        """Return the Account for a key, or None if the key is invalid/missing."""

        if not api_key:
            return None
        target = hash_key(api_key)
        # constant-time scan to avoid leaking which hashes exist
        match: Account | None = None
        for stored_hash, account in self.accounts_by_hash.items():
            if hmac.compare_digest(stored_hash, target) and account.active:
                match = account
        return match

    def resolve_request(self, api_key: str | None) -> tuple[Account | None, str | None]:
        """Resolve a request to an account.

        Returns ``(account, error)`` where error is ``None``, ``"unauthorized"``,
        or ``"rate_limited"``. In open mode an anonymous account is returned.
        """

        account = self.authenticate(api_key)
        if account is None:
            if self.auth_required:
                return None, "unauthorized"
            account = self._anonymous()
        if not self._allow_quota(account):
            return account, "rate_limited"
        return account, None

    # ---- quota ----------------------------------------------------------
    def _allow_quota(self, account: Account, *, now: float | None = None) -> bool:
        limit = account.tier_profile.rate_limit_per_min
        if limit <= 0:
            return True
        now = time.time() if now is None else now
        window = self._hits.setdefault(account.id, deque())
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True

    # ---- factory --------------------------------------------------------
    @classmethod
    def from_env(cls) -> AccountStore:
        """Build a store from environment configuration.

        ``CONDUCTOR_ACCOUNTS_FILE`` — path to accounts YAML (optional).
        ``CONDUCTOR_AUTH_REQUIRED`` — truthy to reject unauthenticated requests.
        ``CONDUCTOR_ANON_TIER``     — tier for anonymous requests (default free).
        """

        auth_required = os.environ.get("CONDUCTOR_AUTH_REQUIRED", "").strip() in {"1", "true", "yes"}
        anon_tier = os.environ.get("CONDUCTOR_ANON_TIER", "free").strip() or "free"
        store = cls(auth_required=auth_required, anon_tier=anon_tier)

        path = os.environ.get("CONDUCTOR_ACCOUNTS_FILE", "").strip()
        if path:
            store.load_accounts_file(Path(path))
        return store

    def load_accounts_file(self, path: Path) -> int:
        """Load accounts from a YAML file. Returns the number of accounts loaded."""

        if yaml is None or not path.is_file():
            return 0
        data = yaml.safe_load(path.read_text()) or {}
        for raw in data.get("accounts", []) or []:
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            key_hash = raw.get("api_key_hash")
            if not key_hash and raw.get("api_key"):
                key_hash = hash_key(str(raw["api_key"]))
            if not key_hash:
                continue
            self.accounts_by_hash[key_hash] = Account(
                id=str(raw["id"]),
                name=str(raw.get("name", raw["id"])),
                tier=str(raw.get("tier", "free")),
                api_key_hash=key_hash,
                active=bool(raw.get("active", True)),
            )
        return len(self.accounts_by_hash)


def account_public_view(account: Account) -> dict:
    """JSON-safe description of an account + its plan + capabilities."""

    plan = account.plan()
    tier = account.tier_profile
    return {
        "id": account.id,
        "name": account.name,
        "tier": account.tier,
        "anonymous": account.anonymous,
        "can_write": account.can_write(legacy_flag=_legacy_writes_flag()),
        "rate_limit_per_min": tier.rate_limit_per_min,
        "surfaces": sorted(tier.surfaces),
        "plan": {"price_usd_month": plan.monthly_price_usd, "description": plan.description},
    }


# --------------------------------------------------------------------------
# Billing seam — provider-plural, defined in conductor_billing.
# Re-exported here for backward compatibility with single-rail callers.
# --------------------------------------------------------------------------
try:  # package-style
    from .conductor_billing import (  # noqa: F401
        BillingProvider,
        NullBillingProvider,
        default_registry,
        get_billing_provider,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from conductor_billing import (  # noqa: F401
        BillingProvider,
        NullBillingProvider,
        default_registry,
        get_billing_provider,
    )
