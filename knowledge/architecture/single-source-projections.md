---
type: Architecture View
title: Fuente única y proyecciones por plataforma
description: Cómo un único conjunto de skills y scripts llega a Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI y Microsoft 365 Copilot.
tags: [arquitectura, contenedores]
status: draft
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Vista

```mermaid
flowchart LR
  SRC[plugin/okf-builder/skills<br/>okf-standard/scripts + templates] 
  SRC -->|symlink .claude/skills| CC[Claude Code]
  SRC -->|symlink .agents/skills| GH[GitHub Copilot]
  SRC -->|symlink .agents/skills| GM[Gemini CLI]
  SRC -->|make plugin → .plugin| CW[Claude Cowork]
  SRC -->|make m365 → zip manifest v1.28| M365[Microsoft 365 Copilot]
  SRC -->|make copilot → .github/skills| OTR[Otros repos]
  K[(knowledge/ del proyecto)] --- CC & GH & GM & CW
  K -->|sync SharePoint/OneDrive| M365
```

# Elementos

| Elemento | Tipo | Responsabilidad | Concepto |
|---|---|---|---|
| Skills fuente | directorio | Instrucciones, plantillas, scripts | [Plugin okf-builder](/systems/plugin-okf-builder.md) |
| Scripts | Python | init, lint, index, migrate | [Scripts OKF](/systems/scripts-okf.md) |
| Exportadores | Python | Proyecciones Copilot y M365 | [Exportadores](/systems/exporters.md) |
| Bundle | directorio | Conocimiento del proyecto | — |

# Principios y restricciones

- Un cambio se hace solo en la fuente; las proyecciones se regeneran (`make all`).
- Los skills usan la convención `<skills>/`; ninguna variable de vendor.
- M365: cada skill autocontenido, ≤20 ficheros companion, sin ficheros ocultos.

# Decisiones relacionadas

* [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md)
