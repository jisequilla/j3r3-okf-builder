---
type: Term
title: Platform package
description: Copy of or link to the source skills, adapted to a platform (symlink, .plugin, M365 zip, Copilot pack).
tags: [domain, glossary, okf]
status: stable
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:55:47Z }, { by: human:jisequilla, at: 2026-11-14T17:30:47Z }]
sources:
  - { id: adr-0022, resource: /base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md }
---

# Definition

Copy of or link to the source skills, adapted to a platform[^adr-0022]. **Link packages** are the symlinks `.claude/skills` and `.agents/skills`; **generated packages** come from `just plugin` (Claude Cowork), `just m365` (Microsoft 365 Copilot) and `just copilot` (a pack to vendor into other repos).

# Where it appears

* [ADR-0007: Single source of skills](/base/decisions/architecture/ADR-0007-single-source-and-projections.md)
* [Exporters](/base/systems/exporters.md)

[^adr-0022]: SDR-0015, decision 6.
