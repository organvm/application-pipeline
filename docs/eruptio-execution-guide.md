# ERUPTIO — Execution Guide

**Date:** 2026-02-18
**Status:** STAGED — all materials ready, awaiting execution
**Purpose:** Break the hermetic seal. Deploy product, submit applications, open revenue channel.
**Planned omega movement:** 8/17 → 10/17 MET (#5, #8, #9). Requires human execution of each action below.

---

## Quick Reference

| # | Action | URL | Deadline | TODO ID | Time |
|---|--------|-----|----------|---------|------|
| 1 | Watermill Center | https://watermillcenter.slideroom.com/ | **TONIGHT 11:59pm EST** | F24 | 45 min |
| 2 | Deploy life-my--midst--in | https://render.com | ASAP | X2 | 10 min |
| 3 | Google CL5 | https://www.creativelab5.com/ | Rolling | X1 | 10 min |
| 4 | Artadia NYC | https://artadia.org (Submittable) | Mar 1 | F3 | 30 min |
| 5 | Doris Duke AMT | https://dorisduke.givingdata.com/portal/campaign/AMT2026 | Mar 2 noon ET | F22 | 45 min |
| 6 | Prix Ars + S+T+ARTS | https://calls.ars.electronica.art/2026/prix/ | Mar 4 | F10/F11 | 30 min |
| 7 | PEN America | https://pen.org/us-writers-aid-initiative/ | Rolling | F12 | 20 min |
| 8 | GitHub Sponsors | https://github.com/sponsors/4444J99/dashboard | ASAP | F1 | 15 min |

---

## 1. WATERMILL CENTER — Feb 18 TONIGHT

**Platform:** SlideRoom | **Fee:** $12

### Materials to upload:
- **Project Proposal PDF:** `materials/work-samples/watermill-proposal.md` — export to PDF, upload (≤5 pages)
- **Artist Statement:** `materials/work-samples/watermill-artist-statement.md` — paste ~200 word version
- **Short Bio:** same file — paste ~75 word version
- **Work Samples:** URLs below

### Work Sample URLs:
| Sample | URL |
|--------|-----|
| Portfolio | `https://4444j99.github.io/portfolio/` |
| System Hub | `https://github.com/meta-organvm` |
| Essays | `https://organvm-v-logos.github.io/public-process/` |
| Generative Art | `https://github.com/organvm-ii-poiesis/metasystem-master` |

### Contingency:
- Tight character limits → trim "The Orchestration" section from proposal first
- Discipline field → "Interdisciplinary — Systems Art / Performance / Digital Media"
- Video required but no time → submit PDF + screenshots instead

### Full script: `scripts/legacy-submission/watermill.md`

---

## 2. DEPLOY life-my--midst--in (X2)

### Steps:
1. Go to https://render.com — sign in with GitHub
2. **New** > **Blueprint** > select `organvm-iii-ergon/life-my--midst--in`
3. Render reads `render.yaml` → provisions `inmidst-web` + `inmidst-api` (both free tier)
4. Click **Apply**

### Environment Variables (on inmidst-api):

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `<REDACTED — rotate credential and set via Render dashboard>` |
| `JWT_SECRET` | `<REDACTED — rotate credential and set via Render dashboard>` |
| `PROFILE_KEY_ENC_KEY` | `<REDACTED — rotate credential and set via Render dashboard>` |
| `NODE_ENV` | `production` |

### Verify:
```
GET <api-url>/health        → {"status":"ok"}
GET <api-url>/ready         → {"status":"ready"}
GET <api-url>/demo/profile  → Full demo profile
```

### After deploy:
- Copy API URL and Web URL
- Copy Deploy Hook URL → add as `RENDER_DEPLOY_HOOK` secret to the repo
- Update `registry-v2.json`: add `"url"`, set `"revenue_status": "beta"`

### Full script: `scripts/legacy-submission/life-deploy.md`

---

## 3. GOOGLE CL5 (X1)

**Platform:** creativelab5.com | **No deadline**

### Paste these answers:

**Q1: "What is a 'rule' of creativity you love breaking?"** (138 words)

> "Creativity requires starting from nothing."
>
> The most interesting creative work I've made came from imposing more constraints, not fewer. My eight-organ system enforces a strict no-back-edges rule: theory feeds art, art feeds commerce — never the reverse. That constraint should limit what's possible. Instead, it forces each organ to be genuinely self-sufficient, which produces work that's stranger and more honest than anything I made when everything could depend on everything else.
>
> The governance model — dependency validation, promotion state machines, automated audits — sounds like the opposite of creative freedom. But designing those rules is where the real creative decisions happen. Choosing how work flows between 103 repositories is as much an artistic act as any individual piece the system produces.
>
> I don't break the rule that creativity needs freedom. I break the rule that constraints aren't creative.

**Q2: "What's the best way to gain perspective?"** (156 words)

> Build the system that reveals the system.
>
> For five years I worked across theory, generative art, commercial products, and community projects without seeing how they related. The relationships were there — code reused between projects, ideas flowing from research to art to products — but they were invisible. When I formalized those relationships into the eight-organ model with explicit dependency rules and a machine-readable registry, patterns I'd never noticed became obvious. Theory was feeding art feeding commerce, but only some of the time, and the failures were as revealing as the successes.
>
> Building in public (ORGAN-V) compounds this. Writing ~6K+ words of documentation forced me to articulate decisions I'd made intuitively. The Aetheria post-mortem — honestly documenting a project that traveled the full Theory->Art->Commerce pipeline and partially failed — taught me more about my practice than any success.
>
> The best way to gain perspective: make the invisible structure explicit, then be honest about what you see.

**Q3: "In 1-3 sentences, tell us about the project you are most proud of and why."** (80 words)

> I built an eight-organ system that coordinates 148 repositories across 8 GitHub organizations — governing how theory, generative art, commercial products, and community work flow into each other through automated dependency validation, a promotion state machine, and ~6K+ words of public documentation. I'm most proud of it because it demonstrates that governance and art aren't separate categories: the rules that coordinate the system are as carefully designed as any artwork it produces. It's infrastructure that makes its own logic visible.

### Links:
| Field | URL |
|-------|-----|
| Portfolio | `https://4444j99.github.io/portfolio/` |
| Resume | `https://4444j99.github.io/portfolio/resume/` |

### Full script: `scripts/legacy-submission/google-cl5.md`

---

## 4. ARTADIA NYC (F3) — Mar 1

**Platform:** Submittable | **Award:** $15,000 unrestricted

### Key fields:
- **Artist Statement** (~250 words): in `scripts/legacy-submission/artadia-nyc.md`
- **Bio/CV** (~100 words): same file
- **Work Samples:** 5 URL-based samples with descriptions (same file)
- **Medium/Discipline:** "New Media / Digital Art / Systems Art"

### Full script: `scripts/legacy-submission/artadia-nyc.md`

---

## 5. DORIS DUKE AMT (F22) — Mar 2 noon ET

**Platform:** Giving Data | **Award:** up to $150,000

### Key fields:
- **Project Title:** "Governance as Performance Score: An AI-Orchestrated Framework for Collaborative Performing Arts Production"
- **Summary** (~250 words): in `scripts/legacy-submission/doris-duke.md`
- **Performing Arts Connection:** same file
- **Bio** (~200 words): same file
- **Budget:** $150K over 8 months (breakdown in script)

### Critical framing note:
This is a **performing arts** grant. Lead with governance-as-choreography, community salons as performance, AI orchestration as conducting. NOT a software grant.

### Full script: `scripts/legacy-submission/doris-duke.md`

---

## 6. PRIX ARS + S+T+ARTS (F10/F11) — Mar 4

**Platform:** calls.ars.electronica.art | **Free** | **Two-for-one** (Prix + S+T+ARTS)

### Key fields:
- **Category:** Digital Humanity (recommended)
- **Project Title:** "The Eight-Organ Creative-Institutional System: Governance as Artistic Medium"
- **Short Description** (~100 words): in `scripts/legacy-submission/prix-ars-starts.md`
- **Extended Description** (~500 words): same file
- **Artist Statement** (~200 words): same file
- **Technical Description** (~150 words): same file

### Full script: `scripts/legacy-submission/prix-ars-starts.md`

---

## 7. PEN AMERICA (F12) — Rolling

**Platform:** pen.org | **Award:** up to $3,500 | **Fit: 9/10**

### Key fields:
- **Professional Writing Credentials:** MFA, 49 essays, ~6K+ words, 11 years teaching
- **Financial Hardship Statement** (~200 words): in `scripts/legacy-submission/pen-america.md`
- **Use of Funds** (~100 words): same file
- **Writing Sample:** Link to public-process essays

### Full script: `scripts/legacy-submission/pen-america.md`

---

## 8. GITHUB SPONSORS (F1)

1. Go to https://github.com/sponsors/4444J99/dashboard
2. Enable Sponsors
3. Set tiers:
   - **$5/mo** — Supporter: name in SUPPORTERS.md, early essay access
   - **$25/mo** — Patron: monthly status updates, input on sprint priorities
   - **$100/mo** — Institutional: logo in README, quarterly architecture review
4. Link portfolio site and public-process in profile description
5. Publish sponsor page

---

## Post-Action Governance Updates — TO BE COMPLETED after execution

After completing each action above, update governance docs:

### rolling-todo.md
- [ ] F24 → mark SUBMITTED with date (Watermill)
- [ ] X2 → mark COMPLETED with date (Render deploy)
- [ ] X1 → mark SUBMITTED with date (Google CL5)
- [ ] F3 → mark SUBMITTED with date (Artadia NYC)
- [ ] F22 → mark SUBMITTED with date (Doris Duke AMT)
- [ ] F10 → mark SUBMITTED with date (Prix Ars Electronica)
- [ ] F11 → mark SUBMITTED with date (S+T+ARTS via Prix Ars)
- [ ] F12 → mark SUBMITTED with date (PEN America)
- [ ] F1 → mark ACTIVATED with date (GitHub Sponsors)

### 04-application-tracker.md
Update each application status from STAGED → SUBMITTED with date. Update summary table counts.

### there+back-again.md (Omega Scorecard)
- **#5** → **MET** when ≥1 application actually submitted
- **#8** → **MET** when life-my--midst--in is live on Render with health check 200
- **#9** → **IN PROGRESS** when GitHub Sponsors is activated
- Update score line accordingly

---

## File Map

All materials are organized under `docs/applications/`:

```
docs/applications/
├── eruptio-execution-guide.md          ← THIS FILE (master checklist)
├── 04-application-tracker.md           ← Status tracking
├── scripts/legacy-submission/
│   ├── watermill.md                    ← Full Watermill script
│   ├── google-cl5.md                   ← Full CL5 script
│   ├── artadia-nyc.md                  ← Full Artadia script
│   ├── doris-duke.md                   ← Full Doris Duke script
│   ├── prix-ars-starts.md              ← Full Prix Ars + S+T+ARTS script
│   ├── pen-america.md                  ← Full PEN America script
│   └── life-deploy.md                  ← Full deploy script
└── materials/work-samples/
    ├── watermill-proposal.md           ← Standalone PDF-ready proposal
    └── watermill-artist-statement.md   ← Standalone artist statement + bio
```
