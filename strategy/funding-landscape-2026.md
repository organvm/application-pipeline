# Funding & Startup Landscape: March 2026 Synthesis

*Compiled: 2026-03-01 | Sources: 262 (see `market-research-corpus.md`) | Algorithmic parameters: `market-intelligence-2026.json` (v2)*

---

## Table of Contents

1. [Landscape Overview](#1-landscape-overview)
2. [Algorithmic Decision Frameworks](#2-algorithmic-decision-frameworks)
3. [Funding Pathway Decision Tree](#3-funding-pathway-decision-tree)
4. [Startup Viability Scorer](#4-startup-viability-scorer)
5. [Differentiation Rubric](#5-differentiation-rubric)
6. [Timing Optimizer](#6-timing-optimizer)
7. [Playbook: Starting a Startup in March 2026](#7-playbook-starting-a-startup-in-march-2026)
8. [Playbook: Non-Dilutive Funding](#8-playbook-non-dilutive-funding)
9. [Playbook: Standing Out](#9-playbook-standing-out)
10. [Calendar of Key Dates](#10-calendar-of-key-dates)
11. [Blind Spots Checklist](#11-blind-spots-checklist)
12. [Pipeline Integration](#12-pipeline-integration)

---

## 1. Landscape Overview

### The Bifurcated Market

The March 2026 landscape is defined by **extreme bifurcation**:

| Dimension | AI-Native Companies | Everything Else |
|-----------|-------------------|-----------------|
| VC availability | Abundant ($202B+ in 2025) | Constrained |
| Seed close time | Weeks (with traction) | 142 days median |
| Valuations | Record highs | Discipline / flat |
| Down-round risk | Low | 17% of rounds |
| Cold application viability | Low everywhere | Very low |

**Key macro numbers:**
- $425B total VC deployed in 2025 (Crunchbase)
- 0.05% of deals capture 50% of dollars
- AI = 48-50% of all venture funding
- 51,330 tech layoffs YTD 2026 (856/day)
- 62% of employers reject generic AI-generated applications
- Warm introductions convert at 58% vs cold at 1-5%

### Five Funding Universes

```
┌─────────────────────────────────────────────────────┐
│                  FUNDING UNIVERSES                    │
├──────────────┬──────────────────┬───────────────────┤
│  DILUTIVE    │  NON-DILUTIVE    │  REVENUE-BASED    │
│              │                  │                   │
│  VC/Angel    │  Grants          │  RBF ($42B mkt)   │
│  SAFEs       │  Fellowships     │  Crowdfunding     │
│  Equity CF   │  Prizes          │  Creator economy  │
│  Accelerators│  Cloud credits   │  Fractional CTO   │
│              │  Gov contracts   │  Consulting       │
└──────────────┴──────────────────┴───────────────────┘
```

---

## 2. Algorithmic Decision Frameworks

All decision frameworks below produce **numeric scores** consumable by pipeline scripts. Parameters reference `market-intelligence-2026.json` keys.

### Framework Design Principles

1. **Every branch terminates in a score** (0-10 scale)
2. **Weights are research-backed** (sourced from 262 citations)
3. **Thresholds are explicit** (no qualitative-only gates)
4. **Fallbacks exist** for missing data (default conservative)

---

## 3. Funding Pathway Decision Tree

### Decision: Which funding path to pursue?

```
START: What is your current state?
│
├── Q1: Do you have revenue? ─── YES ──┐
│                                       │
│   ├── MRR ≥ $10K? ──── YES ──→ SCORE RBF (Section 3.1)
│   │                     NO ──→ Skip RBF
│   │
│   ├── ARR ≥ $300K? ──── YES ──→ SCORE SEED VC (Section 3.2)
│   │                     NO ──→ Skip VC
│   │
│   └── ARR ≥ $1M? ───── YES ──→ SCORE SERIES A (Section 3.3)
│                         NO ──→ Skip Series A
│
├── Q1: No revenue ─────────────────────┐
│                                       │
│   ├── Is it AI-native? ── YES ──→ SCORE AI FUNDING (Section 3.4)
│   │                       NO ──→ Lower base score
│   │
│   ├── Is it open source / public good? ── YES ──→ SCORE CRYPTO GRANTS (Section 3.5)
│   │
│   ├── Does it have artistic/cultural merit? ── YES ──→ SCORE ARTS GRANTS (Section 3.6)
│   │
│   └── Can you work on it part-time? ── YES ──→ SCORE BOOTSTRAP (Section 3.7)
│
└── ALWAYS SCORE:
    ├── Cloud credits (Section 3.8) — non-exclusive, additive
    ├── Fellowships (Section 3.9) — if individual track
    ├── Competitions (Section 3.10) — if showcase-ready
    └── Consulting/fractional (Section 3.11) — as runway hedge
```

### 3.1 Revenue-Based Financing Score

```
BASE_SCORE = 6.0
+ (MRR / 10000) * 0.5          # Higher MRR → higher score (cap at 2.0)
+ (months_history / 12) * 1.0   # Longer history → more options (cap at 1.0)
- (monthly_burn / MRR) * 0.5    # High burn relative to revenue penalized
+ 0.5 if SaaS                   # Preferred by all RBF providers
PROVIDER_MATCH:
  Pipe:     MRR ≥ $10K, US/UK incorporated
  Capchase: ARR ≥ $100K (basic) or $1M (full), 8+ months old
  Clearco:  Revenue ≥ $100K/mo, 12+ months, US incorporated
```

### 3.2 Seed VC Score

```
BASE_SCORE = 4.0  (hard market — 142 day median close)
+ 2.0 if AI-native
+ 1.5 if warm intro available
+ 1.0 if ARR $300-500K
+ 0.5 if solo founder with prior exit
- 1.0 if non-AI SaaS without clear moat
- 1.5 if consumer app
- 0.5 per month under 6 months runway
THRESHOLD: Score ≥ 6.0 → pursue actively
TIMELINE: Plan 5-7 months start-to-close
```

### 3.3 Series A Score

```
BASE_SCORE = 3.0  (Series A squeeze active)
+ 2.5 if ARR $1-5M
+ 1.5 if net revenue retention > 120%
+ 1.0 if AI sector
+ 1.0 if LTV:CAC ≥ 3:1
+ 0.5 if burn multiple < 2x
- 2.0 if seed-to-A gap > 20 months (616 day median)
THRESHOLD: Score ≥ 7.0 → pursue actively
CONVERSION RATE: 36% of 2020-2021 seed cohort converted
```

### 3.4 AI-Specific Funding Score

```
BASE_SCORE = 7.0  (market favors AI)
+ 1.5 if vertical AI (not wrapper)
+ 1.0 if proprietary data advantage
+ 0.5 if multimodal capability
+ 0.5 if defense/health/fintech vertical
- 3.0 if "AI wrapper" without switching costs
- 1.0 if no technical co-founder/advisor
CLOUD CREDITS ADDITIVE:
  Microsoft: +$150K (up to 4yr)
  AWS: +$300K (AI startups)
  Google: +$350K (AI-first)
  NVIDIA: +$100K (AWS credits via partnership)
```

### 3.5 Crypto / Web3 Grants Score

```
BASE_SCORE = 5.0
+ 2.0 if open source with public benefit
+ 1.5 if Ethereum ecosystem contribution
+ 1.0 if prior Gitcoin grant or contribution history
- 2.0 if no public goods angle
PROVIDERS:
  Gitcoin: quadratic funding, continues through ~2029
  Ethereum ESP: $5K-$500K, rolling applications
  Optimism RPGF: retroactive (rewards proven impact)
NOTE: Gitcoin Labs shutting down but Grants Program continues
```

### 3.6 Arts/Creative Grants Score

```
BASE_SCORE = 5.0
+ 2.0 if dual alignment (your practice + funder mission)
+ 1.5 if strong work samples
+ 1.0 if prior grant history
+ 0.5 if institutional partnership
- 1.0 if first-time applicant
- 0.5 if no exhibition/presentation history
ACCEPTANCE RATES:
  Creative Capital: ~5% (109 awards from thousands)
  LACMA Art+Tech: 3-5 projects selected
  S+T+ARTS: 2 Grand Prizes
  Awesome Foundation: 20-30% (monthly, low bar)
```

### 3.7 Bootstrap Score

```
BASE_SCORE = 6.0
+ 2.0 if consulting revenue covers expenses
+ 1.5 if AI reduces build time to 2-4 weeks MVP
+ 1.0 if PLG model viable (ACV < $5K)
+ 0.5 if solo founder (42% of $1M+ revenue companies)
- 1.5 if requires >12 months to first revenue
- 1.0 if hardware-dependent
NOTE: 52.3% of exits are solo-founder companies
```

### 3.8 Cloud Credits (Always Pursue)

```
TOTAL_AVAILABLE = $900K+
Microsoft Founders Hub: $150K (4yr, tiered)
AWS Activate: $100K (standard) or $300K (AI)
Google Cloud: $350K (AI-first) or $200K (non-AI)
NVIDIA Inception: $100K AWS credits + GPU pricing
REQUIREMENT: Incorporated, pre-Series C, working website
ACTION: Apply to all four simultaneously — non-exclusive
```

### 3.9 Fellowship Score

```
BASE_SCORE = 5.0
+ 2.0 if track record in funder's domain
+ 1.0 if systemic / social change angle
+ 0.5 if published / exhibited
- 1.0 if no nomination pathway
TOP PROGRAMS:
  Shuttleworth: $275K/yr (1% acceptance)
  Mozilla: $100K total (nominations closed for 2026)
  TED: network + amplification
  Ashoka: living stipend (rolling)
  Echoing Green: 18 months (watch for 2027 cycle)
```

### 3.10 Competition Score

```
BASE_SCORE = 4.0
+ 2.0 if prototype ready for demo
+ 1.0 if social impact angle
+ 0.5 if team > 1 person
- 1.0 if idea-stage only
TOP PRIZES:
  XPRIZE: $11M (multi-year, self-fund development)
  MIT Solve: ~$40K per team
  Hult Prize: $1M (students)
  MIT $100K: $100K (MIT-affiliated)
```

### 3.11 Consulting / Fractional Score (Runway Hedge)

```
BASE_SCORE = 7.0  (structural market shift)
+ 1.5 if 10+ years experience
+ 1.0 if leadership experience
+ 0.5 if AI/ML expertise
RATES:
  Fractional CTO: $200-500/hr (avg $300/hr)
  Monthly retainers: mid-four to low-five figures
  Market doubled in 2 years — structural, not cyclical
TRIGGER: Activate if full-time search > 3 months
```

---

## 4. Startup Viability Scorer

### Composite Score (0-100)

Weight each dimension, sum to composite:

| Dimension | Weight | Scoring Criteria | Max Points |
|-----------|--------|-----------------|------------|
| **Market Timing** | 20% | AI-native +18, defense/health +15, non-AI SaaS +8, consumer +5 | 20 |
| **Funding Access** | 15% | Warm intros available +12, accelerator +10, cold only +3 | 15 |
| **Solo Founder Viability** | 10% | Prior exit +10, technical +8, first-time +4 | 10 |
| **Revenue Model** | 15% | SaaS +15, marketplace +12, consulting +8, no model +2 | 15 |
| **Differentiation** | 15% | Proprietary data +15, vertical depth +12, workflow integration +10, wrapper +2 | 15 |
| **Runway** | 10% | 24+ months +10, 18-24 +8, 12-18 +5, <12 +2 | 10 |
| **Regulatory Moat** | 5% | EU AI Act compliant +5, compliance tooling +3, none +0 | 5 |
| **Team/Advisor** | 10% | Domain expert advisor +10, technical co-founder +8, solo without advisor +3 | 10 |

**Interpretation:**
- 80-100: **Strong viability** — pursue aggressively
- 60-79: **Moderate viability** — pursue with mitigation plan
- 40-59: **Questionable viability** — consider pivoting model or team
- <40: **Low viability** — fundamental rethink needed

### Key Benchmarks (Research-Backed)

```
AI startup failure rate:              90%
Solo founder success at $1M+ revenue: 42%
Solo founder share of exits:          52.3%
Seed-to-Series A conversion:         36% (2020-21 cohort)
YC acceptance rate:                    1.5%
Seed round median close time:        142 days
```

---

## 5. Differentiation Rubric

### Scoring: How well-positioned are you? (0-10 per dimension)

| Dimension | Weight | Score 0-3 (Weak) | Score 4-6 (Moderate) | Score 7-10 (Strong) |
|-----------|--------|-------------------|---------------------|---------------------|
| **Proof of Work** | 20% | No public artifacts | GitHub + some projects | 113 repos, 23,470 tests, documented system |
| **Narrative Match** | 15% | Generic pitch | Tailored to market stage | Stage-matched narrative + "Why Now" |
| **Warm Path Access** | 20% | Cold outreach only | 2nd-degree connections | Direct warm intros to decision makers |
| **Vertical Depth** | 15% | Horizontal/generic | Category-specific | Deep domain + proprietary data |
| **Social Proof** | 10% | No reviews/press | Some testimonials | 5+ reviews (270% lift), awards, press |
| **AI Authenticity** | 10% | AI wrapper / buzzwords | AI-assisted with human voice | AI-native with clear competitive moat |
| **Dual Alignment** | 10% | Self-serving only | Partial funder alignment | Serves practice AND funder mission |

### Application Channel Optimization

```
CHANNEL PRIORITY (by conversion rate):
1. Referral:        30% success rate (8x cold)    → 80% of effort
2. Direct portal:   8-12% response rate            → 15% of effort
3. Indeed:          20-25% response rate            → 5% of effort
4. LinkedIn Easy:   2-4% response, 0.04% offer     → AVOID as primary

MATERIAL OPTIMIZATION:
- Tailored cover letter: +53% callback
- Follow-up (Day 7-10): +68% offer probability
- 5+ reviews on profile: +270% conversion
- Clear next step in pitch: +22% meetings booked
```

---

## 6. Timing Optimizer

### When to Apply: Temporal Score Adjustments

```python
def timing_score(deadline, effort_level, current_date):
    days_until = (deadline - current_date).days

    # Urgency bands (from market-intelligence-2026.json)
    urgency = {
        "quick":    {"critical": 1, "urgent": 3,  "upcoming": 7},
        "standard": {"critical": 3, "urgent": 7,  "upcoming": 14},
        "deep":     {"critical": 5, "urgent": 10, "upcoming": 21},
        "complex":  {"critical": 7, "urgent": 14, "upcoming": 28}
    }[effort_level]

    if days_until <= urgency["critical"]:
        return 10.0  # DROP EVERYTHING
    elif days_until <= urgency["urgent"]:
        return 8.0   # HIGH PRIORITY
    elif days_until <= urgency["upcoming"]:
        return 6.0   # SCHEDULE THIS WEEK
    else:
        return 4.0   # QUEUE FOR LATER

    # Seasonal adjustments
    # Grant cycles: apply 6-9 months before deadline
    # VC: avoid December and August (holiday dead zones)
    # Job market: May fastest responses (6.0d), October slowest (7.2d)
    # Fundraising: 142-day seed median → start 6+ months before cash need
```

### Fundraising Timeline Calculator

```
CURRENT_RUNWAY_MONTHS = ?
BURN_RATE_MONTHLY = ?
TARGET_RAISE_AMOUNT = ?

# When to start fundraising:
start_fundraising_at = max(
    CURRENT_RUNWAY_MONTHS - 6,   # 6 months before cash out
    0                             # Don't wait if runway < 6 months
)

# Expected close time:
seed_close_days = 142  # median
series_a_close_days = 616  # median from seed

# Runway buffer:
safe_months = CURRENT_RUNWAY_MONTHS - (seed_close_days / 30)
if safe_months < 3:
    ALERT: "Insufficient runway for fundraising. Consider bridge/RBF/consulting."
```

---

## 7. Playbook: Starting a Startup in March 2026

### Phase 1: Foundation (Weeks 1-2)

1. **Incorporate**: Delaware C-Corp ($500-$819 via Stripe Atlas or Clerky)
2. **File 83(b) election**: Within 30 days of stock grant. Missing this is costly.
3. **Open banking**: Mercury or Brex (SVB if established; Brex acquired by Capital One)
4. **Cloud credits**: Apply to all 4 programs simultaneously ($900K+ total available)
5. **Register on SAM.gov**: Even if not pursuing gov contracts now — registration takes time

### Phase 2: Validate (Weeks 2-6)

1. **Build MVP**: AI-assisted, 2-4 week timeline feasible
2. **Customer discovery**: NSF I-Corps model ($50K grant available)
3. **Validate pricing**: PLG if ACV < $5K; sales-led if ACV > $5K
4. **Document everything publicly**: GitHub, blog, technical writing (0.45 signal weight)

### Phase 3: Fund (Weeks 4-12)

1. **Warm intro mapping**: You have ~200+ unrealized warm paths
2. **Pitch deck**: Sequoia structure. "Why Now" slide critical. Bottom-up TAM only.
3. **SAFE terms**: Post-money SAFE at $2-15M cap (88% of pre-seed)
4. **Parallel tracks**: Apply to cloud credits + grants + accelerators simultaneously
5. **Consulting hedge**: Fractional CTO at $200-500/hr if runway tight

### Phase 4: Scale (Months 3-12)

1. **Hit seed traction benchmarks**: $300-500K ARR expected for seed
2. **Plan for 142-day close**: Budget time and emotional energy
3. **Build for Series A gates**: $1-5M ARR, LTV:CAC ≥ 3:1, burn multiple < 2x
4. **Accelerator timing**: YC batch deadlines; 1.5% acceptance → apply early, iterate

### Critical Numbers to Know

| Metric | Value | Source |
|--------|-------|--------|
| Delaware C-Corp formation | $500-$819 | Stripe Atlas / Clerky |
| Post-money SAFE prevalence | 88% at pre-seed | Carta 2025 |
| Seed median close time | 142 days | Carta Q3 2025 |
| Seed median round | $3.1M | PitchBook 2025 |
| Series A median pre-money | $49.3M | Carta Q3 2025 |
| AI share of all VC | 48-50% | Crunchbase/CB Insights |
| Solo founder $1M+ revenue | 42% | startup research |
| AI startup failure rate | 90% | market research |
| YC acceptance rate | 1.5% | YC data |
| Cloud credits available | $900K+ | MS + AWS + Google + NVIDIA |

---

## 8. Playbook: Non-Dilutive Funding

### Tier 1: Apply Immediately (≤ $0 cost, high probability)

| Program | Amount | Action |
|---------|--------|--------|
| Microsoft Founders Hub | $150K credits | Apply online, no VC required for base tier |
| AWS Activate | $100-300K credits | Apply online, provider-backed for higher tier |
| Google Cloud AI | $350K credits | Apply online, AI-first required for max |
| NVIDIA Inception | $100K credits + GPU pricing | Free to join, incorporated + developer required |
| Awesome Foundation | $1K/month | 5-minute application, monthly chapters |

### Tier 2: Apply This Quarter (March-May 2026)

| Program | Amount | Deadline | Acceptance Rate |
|---------|--------|----------|-----------------|
| Creative Capital 2027 | Up to $50K | April 2, 2026 | ~5% |
| LACMA Art+Tech | Up to $50K | April 22, 2026 | 3-5 projects |
| EU Horizon Europe Digital | Up to €4M | April 15, 2026 | 15-30% |
| Innovate UK Robotics | Up to £900K | April 15, 2026 | Varies |
| Knight Foundation Art+Tech | Varies | June 20, 2026 | Varies |

### Tier 3: Monitor & Prepare

| Program | Amount | Status |
|---------|--------|--------|
| SBIR/STTR | $50K-$1.5M | **EXPIRED** — monitor for reauthorization |
| Shuttleworth Fellowship | $275K/year | Next intake Sept 2026 |
| Echoing Green | 18-month fellowship | Watch for 2027 cycle (summer 2026) |
| Gitcoin Grants | Varies (quadratic) | Ongoing through ~2029 |
| Ethereum ESP | $5K-$500K | Rolling applications |
| Optimism RPGF | Varies | Retroactive — build first, apply later |

### Tier 4: Special Categories

| Category | Programs | Note |
|----------|----------|------|
| Disability grants | Various | **Least competitive** category — prioritize if applicable |
| Climate/ESG | $62.6B PE market | Impact framing opens additional channels |
| International | Chile ($15-80K), Estonia, UK | Non-dilutive + visa |

---

## 9. Playbook: Standing Out

### The 60-Second Rule

Every evaluator — VC, grant panelist, hiring manager — makes an initial decision in under 2 minutes:
- Pitch deck: **2 minutes 24 seconds** median review
- GitHub profile: **90 seconds** recruiter scan
- Resume: **8.4 seconds** per Easy Apply (avoid Easy Apply)
- Cover letter: **30-60 seconds** first read

### Storefront Optimization Checklist

- [ ] Lead with numbers: "113 repositories, 23,470 tests, 49 essays"
- [ ] One sentence, one claim — maintain scannability
- [ ] Pin 3-5 strongest projects on GitHub (not 20 incomplete ones)
- [ ] Bottom-up TAM in pitch deck (never top-down "1% of $200B")
- [ ] "Why Now" slide present and compelling
- [ ] Clear next step on every material (+22% meetings booked)
- [ ] Tailored to each recipient — 62% reject generic, 80% reject robotic

### Cathedral Advantage

The deep systemic work (113 repos, 23,470 tests, ~6K+ words, 49 essays, 33 sprints) provides:
1. **Vertical depth** that evaluators demand in 2026
2. **Proprietary data** (the system itself is a dataset)
3. **Authentic narrative** (not AI-generated, not a wrapper)
4. **Proof of work** replacing proof of credentials
5. **Information density** > fine-tuning capability as differentiator

### Channel-Specific Standing Out

**For VCs:**
- Warm intro or nothing (58% vs 1-5%)
- Show burn multiple < 2x, LTV:CAC ≥ 3:1
- "The system is the moat, not the model"
- Bottom-up TAM with customer segment math

**For Grants:**
- Dual alignment: your practice + funder mission
- Work samples are paramount — lead with strongest, not most recent
- Clarity over artspeak — "get to the point"
- Realistic resource requests signal maturity

**For Jobs:**
- 87% of tech recruiters review GitHub
- System design > algorithm puzzles in 2026 interviews
- Platform engineering + AI = lowest competition, highest demand
- Follow up Day 7-10 (+68% offer probability)

**For Crowdfunding:**
- Pre-launch community building is mandatory
- Backers now behave like early investors
- Post-campaign sales (InDemand) increasingly important

---

## 10. Calendar of Key Dates

### Immediate (March 2026)

| Date | Event | Action |
|------|-------|--------|
| March 2 | Creative Capital 2027 opens | Begin application |
| March 4 | S+T+ARTS Prize closes | Submit if applicable |
| March 4 | Prix Ars Electronica closes | Submit if applicable |
| March 5 | NEA FY2027 extended deadline | Submit if applicable |
| Rolling | Cloud credits (4 programs) | Apply to all immediately |

### Q2 2026 (April-June)

| Date | Event | Priority |
|------|-------|----------|
| April 2 | Creative Capital 2027 closes (3PM ET) | HIGH |
| April 15 | EU Horizon Europe Digital Calls | If EU partnership available |
| April 15 | Innovate UK Robotics (£38M) | If UK-registered |
| April 22 | LACMA Art+Tech Lab closes | HIGH |
| May 1 | DARPA Lift Challenge registration | If applicable |
| June 20 | Knight Foundation Art+Tech | MEDIUM |
| June 2026 | Mozilla 2026 Fellows announced | Monitor |

### Q3 2026 (July-September)

| Date | Event | Priority |
|------|-------|----------|
| July 1 | LACMA notifications | Await response |
| July 9 | NEA FY2027 Cycle 2 | If nonprofit partnership |
| Sept 1 | Shuttleworth Fellowship intake | HIGH if applicable |
| Sept 1 | Ashoka Fellowship cycle | If social change angle |
| Sept 2026 | NEW INC 2026-27 begins | Apply in spring |

### Q4 2026 (October-December)

| Date | Event | Priority |
|------|-------|----------|
| Oct 2026 | Echoing Green 2027 opens | MEDIUM |
| Dec 31 | Thiel Fellowship | If ≤ 22 years old |
| Rolling | DARPA SBIR (1st Wed monthly) | If defense angle |
| Rolling | Awesome Foundation | Monthly, low bar |
| Rolling | Canada NRC IRAP | If Canadian entity |

### Watch Items

- **SBIR/STTR Reauthorization**: $4B/year frozen since Oct 2025. When reauthorized → flood of solicitations
- **Humanity AI**: $500M pooled fund (Ford/MacArthur/Mozilla). Watch for open calls.
- **H-1B Changes**: Wage-based lottery + $100K supplemental fee effective Feb 27, 2026. Impacts startup hiring.

---

## 11. Blind Spots Checklist

### Legal & Financial

- [ ] **83(b) election filed within 30 days** of stock grant
- [ ] **Delaware franchise tax**: Use Assumed Par Value method (not Authorized Shares — can be $400K+)
- [ ] **QSBS compliance**: $15M exclusion (OBBBA July 2025), tiered 3/4/5yr vesting, CA does NOT conform
- [ ] **IP assignment**: All contributors must have signed IP assignment agreements
- [ ] **FTC non-compete**: Ban failed — check state-specific enforceability
- [ ] **D&O insurance**: $125/month early is cheap; much more post-incident

### Health & Sustainability

- [ ] **Founder burnout**: 73% prevalence, often undetected. Signs: decision fatigue, cynicism, micro-optimizing
- [ ] **Structured breaks**: Calendar non-negotiable time off
- [ ] **Peer support**: Join founder peer groups (YPO, Founder Collective, local)
- [ ] **Professional support**: Therapist/coach before crisis, not after

### Strategic

- [ ] **Warm intro audit**: Map 200+ unrealized paths before cold outreach
- [ ] **Documentation as leverage**: Public writing generates inbound deal flow (0.45 signal weight)
- [ ] **Open source strategy**: Contributor pipeline doubles as hiring pipeline
- [ ] **Academic partnerships**: STTR requires university partner — valuable for credibility
- [ ] **Disability grants**: Least competitive category — prioritize if applicable
- [ ] **Climate/ESG framing**: $62.6B market opens additional channels
- [ ] **EU AI Act**: Compliance now creates defensibility moat

### Common First-Time Founder Gaps

- [ ] Financial modeling (not just P&L — unit economics, cohort analysis)
- [ ] Term sheet negotiation (know liquidation preferences, anti-dilution provisions)
- [ ] Board management (even with just yourself — document decisions)
- [ ] HR compliance (worker classification, benefits, equity plans)
- [ ] Tax planning (R&D tax credits, QSBS, state nexus)

---

## 12. Pipeline Integration

### How This Feeds the Application Pipeline

The algorithmic parameters in `market-intelligence-2026.json` are consumed by:

| Script | New Parameters Used |
|--------|-------------------|
| `score.py` | `startup_funding_landscape.*`, `differentiation_signals.*` |
| `standup.py` | `meta_strategy.timing_considerations.*` |
| `campaign.py` | `non_dilutive_funding.cloud_credits.*`, timing optimizer |
| `enrich.py` | `differentiation_signals.proof_of_work.*` |
| `market_intel.py` | All new sections via `--startup`, `--funding`, `--differentiation` |
| `funnel_report.py` | `alternative_funding.*` for channel analysis |

### New Quick Commands (Proposed)

| Command | What It Does |
|---------|-------------|
| `startup` | Startup viability score + recommended funding path |
| `funding` | Non-dilutive funding opportunities by deadline |
| `differentiate` | Differentiation rubric score + gap analysis |
| `blindspots` | Blind spots checklist with completion status |

### Scoring Integration

The decision frameworks above can be integrated into `score.py` by adding:

```python
# In score.py, add startup_viability_score():
def startup_viability_score(entry):
    intel = load_market_intelligence()
    score = 0
    # Market timing (20%)
    if entry.get("ai_native"): score += 18
    elif entry.get("sector") in intel["startup_funding_landscape"]["sector_winners_2026"]: score += 15
    # ... (full implementation per Section 4)
    return score / 100  # Normalize to 0-1
```

---

*This document synthesizes 262 sources into actionable decision frameworks. All numeric parameters are cross-referenced in `market-intelligence-2026.json` (v2). Review due: 2026-06-01.*
