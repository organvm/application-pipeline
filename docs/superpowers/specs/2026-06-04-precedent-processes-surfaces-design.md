# Precedent Processes & Surfaces — Product Manifestation Across Domains

**Date:** 2026-06-04
**Status:** Draft
**Scope:** Surface the pipeline's internal precedent processes and their external instances as a domain-agnostic product, with concrete per-domain configurations (academic, market, etc.)
**Companion artifact:** `strategy/domain-surfaces-registry.yaml`

---

## 0. The Mandate

> *Review internal precedent processes; study external instances; all surfaces require
> surfacing; internal + external surfaces; product manifestation; domain implementations:
> academic, market, etc.*

This spec reads that mandate against the system already documented in
`CLAUDE.md`, `docs/thesis/10-generalization.md`, and `strategy/storefront-playbook.md`,
and resolves it into four moves:

1. **Review internal precedent processes** — catalogue the processes this pipeline has
   *already proven*. They are precedents in the legal sense: the first instance that
   establishes a reusable template (§1).
2. **Study external instances** — map the same processes as they appear in other
   institutions, where they are usually informal, ad hoc, or unaudited (§2).
3. **All surfaces require surfacing** — extend the Cathedral → Storefront principle from
   *applications* to *processes*. Every process has an internal surface (how it works) and
   an external surface (how it is presented and consumed); both must be made legible (§3).
4. **Product manifestation across domains** — package the domain-agnostic machinery as a
   product and instantiate it per domain via configuration, not rewriting (§4–§5).

Nothing here invents new machinery. It surfaces machinery that already exists.

---

## 1. Internal Precedent Processes

A *precedent process* is one this pipeline runs in production today and that can serve as
the canonical template when the same shape recurs elsewhere. Four qualify.

### 1.1 The Application Genesis Process (`apply.py` + SPEC-023)

The canonical submission flow (`CLAUDE.md` → "Canonical Application Flow") is a ten-stage
pipeline with quality gates: clearance gate → standards audit → question fetch → answer
generation → cover-letter resolution → outreach validation → overlap check → PDF build →
directory bundle → continuity test. It is governed by **SPEC-023: Process Sequence
Governance** and its pilot SOP (`docs/SOP-application-genesis.md`), which enforces the
Genesis / Evidence / Completion rules: no advance without a linked SOP and target
artifact; advance to `submitted` requires recorded outreach; completion requires PDF +
outreach evidence + process telemetry.

**Why it is a precedent:** it is a fully-specified, evidence-gated, telemetry-recorded
production pipeline. Any other "produce an evaluated, submittable package" process can
adopt its contract (`objective`, `input_conditions`, `output_artifacts`,
`command_sequence`, `quality_gates`, `evidence_required`, `metrics_captured`).

### 1.2 The Evaluative Process (the Self-Governing Evaluative Authority)

The multi-model IRA facility evaluates pipeline quality across 9 dimensions with 4 AI
raters of distinct personas, computing ICC, Cohen's κ, and Fleiss' κ
(`diagnose.py`, `diagnose_ira.py`, `generate_ratings.py`; rubric in
`strategy/system-grading-rubric.yaml`; personas in `strategy/rater-personas.yaml`). It
implements Beer's VSM System 3\* (independent audit) and is **domain-agnostic by design** —
"the pipeline is its first client, not its reason for existing" (`CLAUDE.md`).

**Why it is a precedent:** it is the single most portable process in the system. Ch. 10's
generalization formula separates domain-specific configuration (pipeline, rubric, panel)
from domain-agnostic machinery (agreement, consensus, feedback). This process *is* that
machinery.

### 1.3 The Standards Process (`standards.py`)

Five-level oversight with triad regulators and ≥2/3 quorum, wired into `apply.py` as the
Level 1 gate. A reusable "should this advance?" governor.

**Why it is a precedent:** any pipeline that needs a hard gate before an irreversible
outward action (submission, publication, deployment) can reuse the quorum-of-regulators
pattern rather than reinventing approval logic.

### 1.4 The Academic Process (the SGO)

The Studium Generale ORGANVM (`docs/superpowers/specs/2026-03-17-studium-generale-organvm-design.md`)
intakes questions, researches them, produces tiered works, and *defends them before the
IRA panel acting as Faculty Senate*. This is the evaluative process (§1.2) re-pointed at a
new artifact class (knowledge instead of applications).

**Why it is a precedent:** it is the existence proof that §1.2 already generalizes — the
authority's first non-application client. The SGO is the academic domain implementation
that this spec asks us to surface (§5).

| Precedent process | Mechanism | Governing artifact | Domain-agnostic core |
|-------------------|-----------|--------------------|----------------------|
| Application Genesis | 10-stage gated pipeline | SPEC-023 / SOP-application-genesis | the staged-pipeline-with-gates contract |
| Evaluative Authority | 9-dim × 4-rater IRA | system-grading-rubric / rater-personas | ICC/κ/consensus/feedback |
| Standards | 5-level quorum gate | `standards.py` | quorum-of-regulators approval |
| SGO (academic) | research → defend → publish | SGO design spec | re-pointed evaluative process |

---

## 2. External Instances

The same process shapes occur across institutions, almost always *un-surfaced*: informal,
undocumented, statistically unaudited. Ch. 10.3 already enumerates them; this section
fixes the correspondence so each external instance can be matched to an internal precedent.

| External instance | Domain class | Internal precedent it mirrors | Status in the wild |
|-------------------|--------------|------------------------------|--------------------|
| Academic peer review | academic | Evaluative Authority (§1.2) | ~20% of ICLR'25 / ~12% of Nature Comms reviews already AI-assisted, ad hoc, unaudited (Ch. 10.3.1) |
| Educational grading / grade-norming | academic | Evaluative Authority (§1.2) | rubric-based but rater calibration usually informal (Ch. 10.3.5) |
| Hiring pipelines (employer side) | market | Application Genesis, mirrored (§1.1) | Scan→Match→Build→Apply→Outreach, direction reversed (Ch. 10.3.2) |
| Grant management (funder side) | market | Application Genesis + Evaluative (§1.1/§1.2) | NSF two-criterion review is a coarse rubric (Ch. 10.3.3) |
| Publishing pipelines | market / academic | Application Genesis (§1.1) | manuscript stages map 1:1 (Ch. 10.3.4) |
| CI/CD quality gates | engineering | Standards + Evaluative (§1.3/§1.2) | binary "tests pass?" instead of multi-dimensional quality (Ch. 10.3.6) |

The honest boundary conditions from Ch. 10.5 carry over unchanged: the method requires
decomposable quality criteria, reproducible evidence, meaningful evaluative diversity, and
observable outcomes. Domains lacking these are out of scope, and the generalization claim
remains — per the thesis itself — a structural argument plus single-domain demonstration,
not yet multi-domain empirical validation.

---

## 3. The Surfacing Principle: All Surfaces Require Surfacing

The Cathedral → Storefront philosophy (`strategy/storefront-playbook.md`) was authored for
*applications*: the deep system is the Cathedral, the scannable hook is the Storefront.
This spec generalizes the same move to *processes*.

**Definition.** Every process has two surfaces:

- **Internal surface** — the mechanism: scripts, gates, YAML schemas, telemetry. What the
  operator runs and audits. (The Cathedral of the process.)
- **External surface** — the manifestation: how a consumer in another domain invokes,
  configures, and reads the process without needing its internals. APIs, config schemas,
  reports, dashboards. (The Storefront of the process.)

**"All surfaces require surfacing"** = no internal surface may exist without a corresponding
external surface. A process that can only be run by its author is un-surfaced and therefore
not yet a product. Surfacing is the act of producing the external surface for each internal
one.

| Internal surface (Cathedral) | External surface (Storefront) | Surfaced? |
|------------------------------|-------------------------------|-----------|
| `apply.py` 10-stage flow | SOP contract + `applications/` bundle | ✅ (SPEC-023) |
| IRA machinery (`diagnose_ira.py`) | rubric YAML + persona YAML + ICC report | ✅ within pipeline; ⚠️ not yet a standalone package |
| `standards.py` quorum gate | Level-1 gate result in `apply.py` | ✅ internally; ⚠️ no external API |
| generalization formula (Ch. 10.4) | *(this spec's registry)* `strategy/domain-surfaces-registry.yaml` | ➕ added here |

The first three rows show the pattern is already practiced internally. The gap this spec
closes is the external surface for *other domains* — which is the product manifestation.

---

## 4. Product Manifestation

The product is the domain-agnostic core (§1.2 machinery + the generalization formula of
Ch. 10.4) packaged so a new domain is added by **configuration, not code**. Ch. 10.6.2
already names the target: a standalone `conductor-ira` package (rubric loader, rater
orchestrator, IRA computation, consensus engine, feedback integrator).

The six-step formula is the product's contract:

```
For any domain D:
  1. PIPELINE(D)   — stages with quality gates        ┐ domain-specific
  2. RUBRIC(D)     — k dimensions (obj/subj, weight)  │ (configuration)
  3. PANEL(D)      — m raters (model, provider, persona) ┘
  4. AGREEMENT(D)  — ICC(2,1), Cohen's κ, Fleiss' κ   ┐ domain-agnostic
  5. CONSENSUS(D)  — median, IQR outliers, re-rate     │ (machinery, solved once)
  6. FEEDBACK(D)   — route consensus + outcomes back  ┘
```

**Manifestation, not reinvention.** Steps 4–6 already exist and are tested in this
pipeline. Product manifestation means giving Steps 1–3 a declarative external surface so
that "implement domain D" reduces to writing a registry entry. That registry is the
companion artifact (§5). A future `conductor-ira` package consumes the registry; until that
package exists, the registry is the specification of what each domain implementation
configures.

**Surfacing checklist for any new domain implementation:**

1. Add a registry entry (pipeline stages, rubric dimensions, panel personas).
2. Confirm the four boundary conditions (Ch. 10.5) hold for the domain.
3. Identify the internal precedent it reuses (§1) — never build new machinery.
4. Define the external surface (what the domain's consumer reads: report, gate, dashboard).
5. State the validation status honestly (configured / demonstrated / empirically validated).

---

## 5. Domain Implementations

The companion `strategy/domain-surfaces-registry.yaml` instantiates the formula for the
domains named in the mandate ("academic, market, etc."), grouped by domain class. Each
entry records: the precedent process reused, pipeline stages, rubric dimensions, panel
personas, internal + external surfaces, and validation status.

- **Academic** — peer review, educational grading, and the SGO (the live academic
  implementation). Reuses the Evaluative Authority precedent (§1.2).
- **Market** — employer-side hiring, funder-side grant management, publishing. Reuses the
  Application Genesis and Evaluative precedents (§1.1/§1.2).
- **Engineering (etc.)** — CI/CD quality gates. Reuses the Standards + Evaluative
  precedents (§1.3/§1.2).

The registry is intentionally declarative: it is the external surface of the generalization
formula, readable by an operator deciding which domain to manifest next and (eventually)
loadable by `conductor-ira`. It claims no empirical validation it does not have — every
entry carries an explicit `validation_status`.

---

## 6. Non-Goals

- This spec does **not** build the `conductor-ira` package; it specifies the surface that
  package will consume (Ch. 10.6.2 remains future work).
- It does **not** assert multi-domain empirical validation; it preserves Ch. 10's honest
  status (structural argument + single-domain demonstration).
- It does **not** modify any production pipeline behavior; it is additive documentation
  plus one configuration artifact.

## 7. References

- `CLAUDE.md` — Cathedral → Storefront, three-pillar model, SPEC-023, IRA authority, SGO
- `docs/thesis/10-generalization.md` — generalization formula, external domains, boundary conditions
- `docs/SOP-application-genesis.md` — SPEC-023 pilot SOP (the Application Genesis precedent)
- `strategy/storefront-playbook.md` — the surfacing principle for applications
- `docs/superpowers/specs/2026-03-17-studium-generale-organvm-design.md` — the academic implementation
- `strategy/domain-surfaces-registry.yaml` — companion artifact (this spec's product surface)
