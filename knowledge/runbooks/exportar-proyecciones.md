---
type: Runbook
title: Exportar y entregar proyecciones
description: Cómo generar y entregar el plugin de Cowork, el paquete M365 y el pack para otros repos.
tags: [runbook, release, m365, copilot]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Pasos

| Destino | Comando | Entrega |
|---|---|---|
| Claude Code (este repo) | nada: `.claude/skills` es symlink | `make check-links` |
| Claude Code (otros) | `/plugin marketplace add <owner>/j3r3-okf-builder` | marketplace del repo |
| Claude Cowork | `make plugin` → `okf-builder.plugin` | arrastrar a un chat de Claude (no por iMessage: lo trata como zip desconocido) |
| GitHub Copilot / Gemini (este repo) | nada: `.agents/skills` es symlink | — |
| GitHub Copilot / Gemini (otros repos) | `make copilot` → `dist/copilot/` | copiar en la raíz del repo destino |
| M365 Copilot Cowork | `make m365` → `dist/m365/okf-builder-m365.zip` | admin center → Manage apps → Upload custom app; o `atk install --file-path … --scope Personal` |
| Copilot Studio / Agent Builder | `make m365` → `dist/m365/skills/*.zip` | Build → Skills → Upload a skill |

# Comprobaciones

- `grep -rn '<skills>' dist/` solo debe encontrar la definición de la convención en okf-standard.
- M365: ningún skill supera 20 companions (el exportador falla si ocurre).

# Conocimiento en M365

`knowledge/` no es accesible vía git desde M365: sincronizar a SharePoint/OneDrive y añadir como fuente de conocimiento del agente. La fuente de verdad sigue en el repo.
