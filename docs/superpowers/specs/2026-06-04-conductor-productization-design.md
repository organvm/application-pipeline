# Conductor — Productization Design Specification

**Date:** 2026-06-04
**Status:** Draft (initial build landed)
**Scope:** Turn the application pipeline from a CLI-only system into a product with a
dashboard UI, REST API, MCP, and ACP surfaces — the "product manifestation" called for in
`2026-06-04-precedent-processes-surfaces-design.md`.

---

## 1. Why

The pipeline is a complete, working system — but it has been usable only through a CLI and
an MCP server. A complete product that no one can reach is a cathedral with no doors. This
spec adds the **storefront surfaces** so the engine can be demonstrated, sold, and operated
by people who do not live in a terminal.

This is the direct continuation of the surfacing principle (precedent-processes spec §3):
*every internal surface requires an external surface.* The pipeline's internal surface is
`pipeline_api.py`; this spec gives it the external surfaces a product needs.

**Product name: Conductor** — after the conductor methodology (`docs/thesis/09`) and the
planned `conductor-ira` package (`docs/thesis/10` §10.6.2). One engine, four surfaces.

## 2. Architecture: one engine, four surfaces

```
                      ┌─────────────────────────────┐
                      │   pipeline_api.py (engine)   │  ← clean, dataclass-returning API
                      │  score/advance/validate/...  │     (already powers MCP)
                      └──────────────┬──────────────┘
        ┌──────────────┬─────────────┼─────────────┬───────────────┐
        ▼              ▼             ▼             ▼               ▼
     CLI            REST API      Dashboard       MCP             ACP
  (run.py /        web_api.py     web/ (SPA)   mcp_server.py   acp_server.py
   cli.py)         /docs OpenAPI  served at /  (29 tools)      /agents,/runs
```

The engine is **not duplicated**. Every surface calls the same `pipeline_api` functions,
so behavior, validation, and safety are identical no matter how a user arrives. Adding a
surface never forks the logic.

## 3. Surfaces delivered

### 3.1 REST API — `scripts/web_api.py`
FastAPI app with auto-generated OpenAPI docs at `/docs`. Endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | liveness + write-mode flag |
| GET | `/api/summary` | KPI aggregates (counts by status/track, avg score) |
| GET | `/api/entries?status=&track=` | summarized, filtered entry list |
| GET | `/api/entries/{id}` | full entry detail |
| GET | `/api/standup` `/api/followups` `/api/hygiene` `/api/triage` | operational views |
| POST | `/api/entries/{id}/score` `/advance` `/validate` `/submit` | state-machine actions |

### 3.2 Dashboard UI — `scripts/web/`
Zero-build SPA (HTML + vanilla JS + CSS, no Node toolchain) served at `/` by the same app.
KPI cards, a filterable pipeline table, live standup, and per-entry View/Score/Validate
actions. Chosen over a React/Vite build to keep the product a single Python deployable.

### 3.3 MCP — `scripts/mcp_server.py` (pre-existing)
29 tools over `pipeline_api`. Unchanged; documented here as one of the four surfaces.

### 3.4 ACP — `scripts/acp_server.py`
Agent Communication Protocol surface: agent manifest at `/agents`, synchronous runs at
`POST /runs` with ACP message/part shapes. Routes a small command grammar
(`summary | entries | standup | followups | hygiene | triage | score <id>`) to the engine.

## 4. Safety & auth model (`scripts/conductor_auth.py`)

- **Per-account authentication + tiers.** Accounts load from a YAML file
  (`CONDUCTOR_ACCOUNTS_FILE`); requests authenticate with `X-API-Key` or
  `Authorization: Bearer`. Each account has a tier (`free`/`pro`/`studio`/`institution`)
  defining write capability, rate limit, and allowed surfaces.
- **Writes are gated by plan, not a global flag.** A state-machine action persists only if
  the calling account's tier permits writes (`pro`+). The free→pro boundary *is* the
  write/no-write boundary — the monetization seam.
- **Backward compatible / open mode.** With no accounts file and `CONDUCTOR_AUTH_REQUIRED`
  unset, every request resolves to an anonymous `free` account whose write capability still
  honors the legacy `CONDUCTOR_ALLOW_WRITES` flag — single-user/dev deployments work
  unchanged.
- **Quota.** Per-account sliding-window rate limiting by tier (free 30/min … institution
  unlimited); exceeding it returns `429`.
- **Billing seam.** `BillingProvider` protocol + `NullBillingProvider` and a `PLANS`
  registry (tier → price). `GET /api/account` returns the account, plan, and a checkout URL
  stub — the documented attach point for a real provider (Stripe). No real charge is wired.
- The dashboard surfaces the current write-mode as a header badge.
- FastAPI is an **optional** dependency (`pip install -e ".[web]"`). `web_api.py`,
  `acp_server.py`, and `conductor_auth.py` import without it (apps built lazily in
  `create_app()`), so module discovery, the verification matrix, and non-web tooling never
  break.

## 5. Running it

```bash
pip install -e ".[web]"
python scripts/run.py serve   # REST API + dashboard → http://127.0.0.1:8000  (docs: /docs)
python scripts/run.py acp     # ACP agent          → http://127.0.0.1:8001  (manifest: /agents)
```

## 6. Testing & CI

- `tests/test_web_api.py`, `tests/test_acp_server.py`: pure helpers tested unconditionally;
  HTTP surfaces use `pytest.importorskip("fastapi")` so they run wherever the `web` extra is
  installed and skip cleanly in the default CI job.
- Satisfies the verification-matrix gate (each new module has a direct test file).

## 7. Monetization (see `docs/ventures/conductor-saas-pricing.md`)

The four surfaces map to revenue tiers: dashboard (self-serve subscription), API/MCP/ACP
(usage- or seat-based for power users and agent builders), and the domain-surfaces registry
(`strategy/domain-surfaces-registry.yaml`) as the path to vertical editions (academic,
market, engineering) per the generalization formula.

## 8. Status of the "honest gaps"

| Gap (as flagged) | Status |
|------------------|--------|
| Authentication | ✅ Landed — API-key auth, `CONDUCTOR_AUTH_REQUIRED` (`conductor_auth.py`) |
| Tier-gated writes | ✅ Landed — per-account capability replaces the global flag |
| Quota / rate limiting | ✅ Landed — per-account sliding window by tier (`429` on exceed) |
| Billing | ◑ **Seam only** — plans + `BillingProvider` protocol + `NullBillingProvider`; no real charge |
| Multi-tenant **data isolation** | ✗ Not yet — see below |
| React/Vite build | ✗ By choice — SPA is intentionally zero-build |
| ACP async/streaming + run persistence | ✗ Not yet — sync-only, in-memory runs |

### Remaining gap: data isolation
Auth/quota/billing are now per-account, but the **data layer is still single-tenant** —
`pipeline_lib` reads one shared set of YAML directories. True multi-tenancy needs a
per-account data root (e.g. `PIPELINE_ROOT` threaded through `load_entries`), which is a
larger change to the core loaders. This is the next gap to close before hosting multiple
paying tenants on one deployment.

## 9. References

- `docs/superpowers/specs/2026-06-04-precedent-processes-surfaces-design.md` — the surfacing mandate
- `scripts/pipeline_api.py` — the shared engine
- `scripts/mcp_server.py` — the existing MCP surface
- `docs/thesis/09-conductor-methodology.md`, `docs/thesis/10-generalization.md` — the name and the generalization
