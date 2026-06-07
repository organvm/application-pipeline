---
title: "Multi-organ governance rules and promotion criteria"
category: projects
tags: [ai, api, ci-cd, formal-systems, governance, python, recursive, symbolic, testing, typescript]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
tier: full
review_status: auto-generated
stats:
  languages: [shell]
  ci: true
  public: false
  promotion_status: CANDIDATE
  relevance: CRITICAL
---

# Project: Multi-organ governance rules and promotion criteria

## One-Line
Multi-organ governance rules and promotion criteria

## Short (100 words)
Multi-organ governance rules and promotion criteria. A theoretical and operational framework for autonomous system governance -- formalising the principles by which a multi-organ creative-institutional system regulates itself without centralised authority. Part of ORGAN-I (Theoria).

## Full
**Problem Statement:** A multi-organ creative-institutional system faces a governance dilemma that no single tool can resolve. Consider what breaks without a formal governance framework: **Consistency collapse.** When 149 repositories across eight GitHub organisations each invent their own security policies, issue templates, and CI pipelines, the result is a patchwork of incompatible standards. A contributor moving from an ORGAN-II art repository to an ORGAN-III commercial product encounters different review norms, different labelling schemes, different quality gates. Cognitive load multiplies; contribution rates decline. **Silent drift.** Without centralised governance primitives, individual repos accumulate configuration debt. Dependabot schedules diverge. Pre-commit hooks cover different subsets of checks. Security scanning tools are present in some repos and absent in others. The system drifts from its own standards without any single actor noticing, because no single actor holds the complete picture. **Decision bottlenecks.** In a system where a human maintainer is the sole governance authority (bus factor of one), every merge, every policy change, every security response routes through a single point of failure. Autonomous governance means encoding decision criteria into machine-readable rules so that routine decisions execute without human intervention, while exceptional decisions surface clearly for human judgement. **Governance theatre.** The worst failure mode is the presence of governance artefacts -- badges, templates, policy documents -- without the enforcement machinery to make them real. A `SECURITY.md` that provides no contact mechanism, a Dependabot configuration that monitors ecosystems with no corresponding dependency files, a CodeQL matrix that scans languages the project does not contain -- these are not governance. They are its simulation. This repository exists to solve all four problems simultaneously: to provide a *theoretically grounded, operationally enforced* governance layer that is composable across organs, self-validating, and honest about its own coverage. ---

**Core Concepts:** ### 1. Governance as Epistemology Traditional governance frameworks ask "what rules should we enforce?" This framework begins one level deeper: "how does a distributed system *know* that it is governed?" The question is epistemological -- it concerns the conditions under which governance claims are justified. The answer this framework provides is *machine-verifiable evidence*. Every governance claim (security scanned, dependencies current, code reviewed) must be backed

## Links
- GitHub: https://github.com/organvm-i-theoria/system-governance-framework
- Organ: ORGAN-I (Theoria) — Theory
