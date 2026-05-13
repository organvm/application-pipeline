---
title: "Documentation Engineer"
category: framings
tags: [documentation, technical-writing, docs-as-code, content-architecture, writing, composition, information-architecture]
identity_positions: [documentation-engineer]
tracks: [job]
related_projects: [organvm-system, portfolio, public-process]
tier: single
---

# Framing: Documentation Engineer

**For:** Developer documentation roles, technical writer positions, docs-as-code infrastructure, content architecture, knowledge management
**Identity position:** Documentation architect who treats structured writing as a typed, validated engineering discipline

## Opening

810,000 words of public documentation across 113 repositories. CLAUDE.md, GEMINI.md, and AGENTS.md auto-generated for every active repo from Jinja2 templates bound to live registry data. Variable binding that propagates code file counts, test totals, and organ membership into context files without manual edits. An MFA in Creative Writing and 11 years teaching composition to 2,000+ students — and 49 published essays on the intersection of systems, language, and culture.

**Pattern interrupt note:** Lead with the architecture numbers before naming the writing background. "MFA" fires a "not technical" pattern — delay it until after the docs-as-code infrastructure has registered. The argument is: this person treats documentation as a typed system contract, not a narrative deliverable.

## Key Claims

- **Scale:** ~6K+ words of structured documentation across 148 repos — not padded prose, but architecture plans, SOPs, session logs, governance rules, registry data, and generated context files
- **Auto-generation:** contextmd system generates CLAUDE.md/GEMINI.md/AGENTS.md from templates + registry; no manual sync across the system
- **Variable binding:** Live metrics (22,885 code files, 2,349 test files, 104 CI/CD workflows) propagate into all documentation automatically via Python binding layer
- **Validation:** Every doc format has a JSON Schema contract; automated CI validation on all corpus docs
- **Process governance:** praxis-perpetua corpus — 6 SOPs, 5 templates, session self-critique logs; institutional knowledge as versioned, structured docs not team convention
- **Teaching:** 11 years, 100+ courses, 2,000+ students — composition, rhetoric, writing at scale is the same discipline as documentation architecture

## Lead Evidence

- organvm-corpvs-testamentvm: ~6K+ words, validation scripts, 2,240-line registry-v2.json with JSON Schema
- contextmd/generator.py: Auto-generation engine — Jinja2 templates + registry data + variable resolution
- metrics/propagate.py: Variable binding pipeline that pushes computed metrics into markdown/JSON docs
- praxis-perpetua/: 6 SOPs, 5 templates, session archive — process docs treated as first-class artifacts
- Portfolio: 20 case studies with consistent schema (problem, approach, evidence, outcome), Pagefind search
- Teaching record: 8 institutions, 11 years, 100+ composition courses

## What to Acknowledge

- Not a dedicated technical writer by prior job title — documentation engineering emerged from systems architecture practice
- No enterprise docs platform experience (Confluence, Notion, Readme.io) — all docs-as-code in git/Markdown
- Independent practice — no peer review with other writers or doc engineers
- "~6K+ words" includes generated/templated content, not all original prose

## Documentation-Resume Translation

| System Artifact | Engineering Frame |
|-----------------|-------------------|
| contextmd auto-generation | Docs-as-code pipeline: templates → registry data → published context files |
| Variable binding system | Live metrics propagation — documentation never goes stale |
| JSON Schema validation in CI | Typed documentation contracts with automated validation gates |
| praxis-perpetua SOPs | Institutional knowledge as structured, versioned, auditable artifacts |
| 11 years teaching composition | Communication at scale — same discipline as developer documentation |
| 49 essays published | Long-form technical and analytical writing with public record |
