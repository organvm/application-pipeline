---
title: "Platform Orchestrator"
category: framings
tags: [platform-engineering, orchestration, developer-experience, registry, infrastructure, devex, mcp]
identity_positions: [platform-orchestrator]
tracks: [job]
related_projects: [organvm-system, organvm-engine, organvm-mcp-server]
tier: single
---

# Framing: Platform Orchestrator

**For:** Platform engineering, developer productivity, engineering effectiveness, systems architecture
**Identity position:** Platform architect who designed infrastructure-of-infrastructure for one-person institutional-scale operation

## Opening

I designed an orchestration system that coordinates 149 repositories across 8 GitHub organizations through a machine-readable registry, automated dependency validation, seed.yaml contracts declaring produces/consumes edges, and a pulse daemon computing system density every 15 minutes across 1,833 tracked entities. An MCP server with 88 tools exposes the full system graph to any AI agent session. The system exists so one person can steer 113 repos with the coherence a team of 10 would bring — and the infrastructure that makes this possible is the most interesting engineering artifact.

**Key framing note:** Emphasize the architecture, not the code. The distinctive thing isn't writing Python — it's designing a system where registry, contracts, governance, and observability compose into something one person can actually operate.

## Key Claims
- **Registry architecture:** registry-v2.json as single source of truth for all 113 repos (2,200+ lines)
- **Seed contracts:** Every repo declares its produces/consumes edges and event subscriptions via seed.yaml
- **Pulse daemon:** 15-minute heartbeat computing AMMOI density, recording observations to Neon, evaluating advisory policies
- **MCP server:** 88 tools across 16 groups exposing the full system graph to AI sessions
- **Superproject management:** Git superproject with submodule sync, drift detection, workspace reproduction
- **Context generation:** Auto-generated CLAUDE.md/GEMINI.md/AGENTS.md across all repos from templates + live variables

## Lead Evidence

- organvm-engine: 2,556 tests, 21 domain modules, 23 CLI command groups
- ontologia: 1,833 entities, 1,843 edges, adaptive structural registry
- AMMOI density index: compressed multi-scale system state text
- Variable binding system: `<!-- v:KEY -->` markers resolved across 171 files
- Neon metrics sink: time-series observations queryable by stakeholder portal

## What to Acknowledge
- Infrastructure serves one operator (no multi-tenant)
- Scale is in breadth (113 repos) not traffic (no production users)
- The platform IS the product — this is infrastructure-as-practice
