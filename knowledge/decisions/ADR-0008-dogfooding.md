---
type: Architecture Decision
title: "ADR-0008: The okf-builder repo documents its own knowledge with OKF"
description: This repository applies profile knowledge/1.0 to itself; the project's decisions are ADRs in knowledge/decisions.
tags: [adr, process]
status: stable
adr_id: ADR-0008
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

The design decisions for the standard and the plugin lived in conversations with the agent. A knowledge standard that is not used on itself is neither credible nor truly tested.

# Decision

`knowledge/` at the root of this repo, conformant with the profile, validated in `make lint` with `--strict`. Any agent working in the repo reads `knowledge/index.md` first (rule in [AGENTS.md](/policies/agents-in-this-repo.md)). Decision changes are recorded as new ADRs that supersede the previous one.

# Consequences

- Positive: the standard is tested in real use; agents on any platform inherit the context; the decision history can be queried.
- Negative: maintenance discipline; mitigated because `okf-capture` and `okf-lint` do the mechanical work.
