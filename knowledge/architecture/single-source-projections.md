---
type: Architecture View
title: Single source and per-platform projections
description: How a single set of skills and scripts reaches Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot.
tags: [architecture, containers]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# View

```mermaid
flowchart LR
  SRC[plugin/okf-builder/skills<br/>okf-standard/scripts + templates] 
  SRC -->|symlink .claude/skills| CC[Claude Code]
  SRC -->|symlink .agents/skills| GH[GitHub Copilot]
  SRC -->|symlink .agents/skills| GM[Gemini CLI]
  SRC -->|make plugin → .plugin| CW[Claude Cowork]
  SRC -->|make m365 → zip manifest v1.28| M365[Microsoft 365 Copilot]
  SRC -->|make copilot → .github/skills| OTR[Other repos]
  K[(project knowledge/)] --- CC & GH & GM & CW
  K -->|sync SharePoint/OneDrive| M365
```

# Elements

| Element | Type | Responsibility | Concept |
|---|---|---|---|
| Source skills | directory | Instructions, templates, scripts | [okf-builder plugin](/systems/plugin-okf-builder.md) |
| Scripts | Python | init, lint, index, migrate | [OKF scripts](/systems/scripts-okf.md) |
| Exporters | Python | Copilot and M365 projections | [Exporters](/systems/exporters.md) |
| Bundle | directory | Project knowledge | — |

# Principles and constraints

- A change is made only in the source; projections are regenerated (`make all`).
- Skills use the `<skills>/` convention; no vendor variable.
- M365: each skill is self-contained, with ≤20 companion files and no hidden files.

# Related decisions

* [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md)
