---
type: Architecture Decision
title: "ADR-0003: Directorios y tipos del perfil en español"
description: Los directorios del perfil y los valores de type van en español, salvo references/ y Attested Computation que fija la spec.
tags: [adr, estructura]
status: deprecated
adr_id: ADR-0003
decision_status: superseded
superseded_by: /decisions/ADR-0010-english-canonical-profile-2.md
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

El usuario del estándar y sus equipos trabajan en español. La spec OKF no impone nombres de directorio ni registra tipos.

# Decisión

Directorios en español (`decisiones/`, `runbooks/`, `politicas/`…) y tipos en español (`Decisión de Arquitectura`, `Métrica`…). Se mantienen en inglés solo los nombres que la spec fija o usa como convención: `references/` (§6.3) y `type: Attested Computation` (§10).

# Consecuencias

- Positivas: legibilidad para los equipos; los índices y descripciones son coherentes en un idioma.
- Negativas: los ejemplos de la spec y los bundles de Google usan inglés; los consumidores deben tolerar tipos desconocidos (la spec lo exige, §11).
