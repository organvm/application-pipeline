# Conductor — Monetization & Go-to-Market

**Date:** 2026-06-04
**Status:** Draft strategy
**Premise:** Ship and charge. No more complete products locked in a drawer waiting for
perfection. Conductor is the productized application pipeline — a working engine with a
dashboard, REST API, MCP, and ACP surfaces (see
`docs/superpowers/specs/2026-06-04-conductor-productization-design.md`).

---

## 1. What we are selling

A precision pipeline that finds perfect-fit opportunities (jobs, grants, residencies,
fellowships), scores them across 9 dimensions, composes tailored materials, and tracks
relationships — with an evaluative authority (multi-model IRA) that audits its own quality.
The differentiator is **precision over volume** and a governed, auditable process, not a
spray-and-pray application bot.

## 2. Surfaces → revenue mapping

| Surface | Who it serves | Monetization |
|---------|---------------|--------------|
| **Dashboard UI** | Individual applicants / artists | Self-serve subscription (Free → Pro → Studio) |
| **REST API + OpenAPI** | Power users, integrators, careers services | Usage- or seat-based add-on |
| **MCP server** | People driving the pipeline from Claude / agent IDEs | Bundled with Pro+ |
| **ACP agent** | Agent builders composing multi-agent workflows | Usage-based (per run) |
| **Domain-surfaces registry** | Institutions (universities, funders, employers) | Vertical editions / licensing |

## 3. Tiers (initial hypothesis — validate, don't overfit)

| Tier | Price (hypothesis) | Includes |
|------|--------------------|----------|
| **Free** | $0 | Dashboard read-only, 1 active track, manual scoring |
| **Pro** | ~$19/mo | Writes enabled (`CONDUCTOR_ALLOW_WRITES`), all 9 dimensions, MCP access, full composition |
| **Studio** | ~$49/mo | API + ACP access, unlimited tracks, IRA quality audits, analytics suite |
| **Institution** | Custom | Vertical editions (academic peer-review, employer-side hiring, grant management) from the generalization formula |

Numbers are starting points for price discovery, not committed pricing. The Free → Pro
seam is exactly the `CONDUCTOR_ALLOW_WRITES` flag already implemented: read is free, write
(persisting state-machine actions) is the paid action.

## 4. Vertical editions (the institution play)

`strategy/domain-surfaces-registry.yaml` already encodes how the same engine instantiates
for other domains. Each `validation_status: configured` domain is a candidate edition:

- **Academic** — peer-review pre-screening, grade-norming (sell to journals, departments)
- **Market** — employer-side hiring scorecards, funder-side grant review (sell to recruiters, foundations)
- **Engineering** — CI/CD multi-dimensional quality gates (sell to platform teams)

Productization path per edition: promote `configured` → `demonstrated` (run on real data) →
`validated` (multi-rater empirical ICC) before charging institutional prices.

## 5. Honest status

- The pipeline and all four surfaces work today; billing, auth, and multi-tenancy are not
  built yet (the write-flag is the seam where they attach).
- Conversion benchmarks cited in `CLAUDE.md` (8x referral, +53% cover-letter) are *market*
  benchmarks, not Conductor's own validated metrics. Pricing claims must not overstate them.
- First revenue motion is self-serve (dashboard subscription); institutional/vertical sales
  follow once at least one domain reaches `demonstrated`.

## 6. Next steps

1. ~~Add authentication + per-account write-gating on top of `CONDUCTOR_ALLOW_WRITES`.~~
   ✅ Done — `scripts/conductor_auth.py` (API-key auth, tiers, quota, billing seam).
2. Wire a real billing provider into the `BillingProvider` seam (Stripe checkout +
   webhook → set `tier`); persist accounts in a database rather than a YAML file.
3. Close the data-isolation gap: per-account `PIPELINE_ROOT` so tenants don't share data.
4. Deploy the FastAPI app (single container) behind a managed host.
5. Instrument the dashboard for activation/retention to run real price discovery.
6. Promote one registry domain to `demonstrated` to open the institutional tier.
