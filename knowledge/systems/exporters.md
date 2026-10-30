---
type: System
title: Exportadores de proyecciones
description: tools/export_copilot.py y tools/export_m365.py generan las proyecciones de los skills para otros repos y para Microsoft 365 Copilot.
resource: /tools
tags: [sistema, exportadores, m365, copilot]
status: draft
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Responsabilidad

| Exportador | Salida | Para |
|---|---|---|
| export_copilot.py | `dist/copilot/.github/skills`, `.github/agents/okf.agent.md`, `AGENTS.okf.md` | Vendorizar skills en otro repo (Copilot, Claude, Gemini) |
| export_m365.py | `dist/m365/okf-builder-m365.zip` (manifest v1.28) y `dist/m365/skills/*.zip` | Plugin Cowork M365 y subida por skill en Copilot Studio / Agent Builder |

# Reglas que aplican

- Sustituyen la convención `<skills>/` por la ruta concreta del destino.
- M365: copian en cada skill los scripts/plantillas que necesita (tabla `NEEDS`), eliminan `scripts/` de okf-standard para respetar el límite de 20 companions, añaden `license`/`metadata` y una nota de entorno.
- El manifest M365 usa GUID estable (uuid5 de la URL del repo).

# Operación

* [Exportar y entregar proyecciones](/runbooks/export-projections.md)
* Decisión: [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md)
