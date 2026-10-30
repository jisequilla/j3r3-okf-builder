---
type: Policy
title: Reglas para agentes que trabajan en este repo
description: Obligaciones de cualquier agente (Claude, Copilot, Gemini, M365) al modificar este repositorio; es el contenido normativo de AGENTS.md.
resource: /AGENTS.md
tags: [politica, agentes]
status: draft
owner: human:jisequilla
stale_after: 2027-10-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Norma

1. Leer `knowledge/index.md` y los ADRs antes de cambiar estándar, skills o scripts.
2. Un cambio de decisión es un ADR nuevo que sustituye al anterior; nunca se edita la historia.
3. Editar solo la fuente `plugin/okf-builder/skills/`; nunca las proyecciones (`.claude/skills`, `.agents/skills`, `dist/`).
4. Terminar con `make test` (código) y `make lint` (conocimiento).
5. No usar variables de vendor en skills; convención `<skills>/`.
6. No añadir `verified: human:` sin confirmación de la persona ([ADR-0005](/decisions/ADR-0005-required-generated-human-verified.md)).

# Relacionados

* [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md) · [ADR-0008](/decisions/ADR-0008-dogfooding.md)
