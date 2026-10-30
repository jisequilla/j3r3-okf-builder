---
type: Architecture Decision
title: "ADR-0007: Fuente única de skills y proyecciones por plataforma"
description: Los skills viven una sola vez en plugin/okf-builder/skills; cada plataforma recibe una proyección (symlink o paquete generado).
tags: [adr, arquitectura]
status: stable
adr_id: ADR-0007
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

El mismo conocimiento operativo debe funcionar en Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI y Microsoft 365 Copilot. Todas adoptan el estándar Agent Skills (`SKILL.md`), pero cada una lo descubre o empaqueta de forma distinta y tiene límites propios (M365: ≤20 ficheros companion por skill, skills autocontenidos). Mantener copias por plataforma divergiría.

# Decisión

- **Fuente única**: `plugin/okf-builder/skills/`. Scripts en `okf-standard/scripts/`, plantillas en `okf-standard/templates/`.
- Los skills no usan variables de ningún vendor; usan la convención `<skills>/...` (padre del skill).
- **Proyecciones por enlace**: `.claude/skills` y `.agents/skills` → fuente (Claude Code; Copilot y Gemini).
- **Proyecciones generadas**: `make plugin` (Cowork), `make m365` (M365, autocontenido por skill), `make copilot` (pack vendorizable). Salida en `dist/`, no versionada.
- Ver [vista de arquitectura](/architecture/single-source-projections.md).

# Alternativas consideradas

| Alternativa | Contras | Motivo de descarte |
|---|---|---|
| Copias por plataforma en el repo | Divergen; 5× mantenimiento | Es el problema que se quiere evitar |
| Solo plugin de Claude + conversores de terceros (`atk import openplugin`, `wiqd`) | No reescriben rutas ni reparten scripts | Insuficiente para M365 |

# Consecuencias

- Positivas: un cambio, todas las plataformas; `make check-links` y `make all` lo verifican.
- Negativas: symlinks requieren `core.symlinks` en Windows; en ese caso usar `make copilot` y copiar.
