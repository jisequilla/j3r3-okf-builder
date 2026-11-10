---
type: Architecture View
title: Single source and per-platform packages
description: How a single set of skills and scripts reaches Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot.
tags: [architecture, containers]
status: stable
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:34:38Z }
verified: { by: human:jisequilla, at: 2026-11-10T22:37:33Z }
---

# View

```mermaid
flowchart LR
  SRC[plugin/okf-builder/skills<br/>okf-standard/scripts + templates] 
  SRC -->|symlink .claude/skills| CC[Claude Code]
  SRC -->|symlink .agents/skills| GH[GitHub Copilot]
  SRC -->|symlink .agents/skills| GM[Gemini CLI]
  SRC -->|just plugin → .plugin| CW[Claude Cowork]
  SRC -->|just m365 → zip manifest v1.28| M365[Microsoft 365 Copilot]
  SRC -->|just copilot → .github/skills| OTR[Other repos]
  K[(project knowledge/)] --- CC & GH & GM & CW
  K -->|GitHub connector or SharePoint source| M365
```

# Elements

| Element | Type | Responsibility | Concept |
|---|---|---|---|
| Source skills | directory | Instructions, templates, scripts | [okf-builder plugin](/base/systems/plugin-okf-builder.md) |
| Scripts | Python | init, lint, index, migrate | [OKF scripts](/base/systems/scripts-okf.md) |
| Exporters | Python | Copilot and M365 packages | [Exporters](/base/systems/exporters.md) |
| Bundle | directory | Project knowledge | — |

# Principles and constraints

- A change is made only in the source; platform packages are regenerated (`just all`).
- Skills use the `<skills>/` convention; no vendor variable.
- M365: each skill is self-contained, with ≤20 companion files and no hidden files.

# Related decisions

* [ADR-0007](/base/decisions/ADR-0007-single-source-and-projections.md)
