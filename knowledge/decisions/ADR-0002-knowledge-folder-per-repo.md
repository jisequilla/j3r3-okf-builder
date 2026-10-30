---
type: Architecture Decision
title: "ADR-0002: Un bundle por repositorio en knowledge/"
description: Cada repo lleva su conocimiento en knowledge/ co-localizado con el código, no en un repo central.
tags: [adr, estructura]
status: stable
adr_id: ADR-0002
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

Opciones: bundle dentro de cada repo, repo central de conocimiento, o híbrido con índice agregado.

# Decisión

**Dentro de cada repo**, en `knowledge/` en la raíz. El bundle viaja con el código, se revisa en los mismos PR y los agentes que trabajan sobre el repo lo encuentran sin configuración.

# Consecuencias

- Positivas: versionado y revisión unificados; descubrimiento trivial (`knowledge/index.md`).
- Negativas: la vista transversal entre proyectos no existe de serie; si hace falta, un consumidor puede agregar varios bundles (fuera de alcance, ver [proyecto](/project.md)).
