---
type: Term
title: Platform package
description: Copy of or link to the source skills, adapted to a platform (symlink, .plugin, M365 zip, Copilot pack).
tags: [domain, glossary, okf]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:15:00Z }
sources:
  - { id: adr-0019, resource: /decisions/ADR-0019-knowledge-projections.md }
---

# Definition

Copy of or link to the source skills, adapted to a platform[^adr-0019]. **Link packages** are the symlinks `.claude/skills` and `.agents/skills`; **generated packages** come from `make plugin` (Claude Cowork), `make m365` (Microsoft 365 Copilot) and `make copilot` (a pack to vendor into other repos).

# Where it appears

* [ADR-0007: Single source of skills](/decisions/ADR-0007-single-source-and-projections.md)
* [Exporters](/systems/exporters.md)

[^adr-0019]: ADR-0019, decision 6.
