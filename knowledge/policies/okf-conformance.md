---
type: Policy
title: Conformidad con el perfil knowledge/2.0
description: Todo bundle que produzca o toque este proyecto debe pasar okf_lint --strict en su versión declarada.
tags: [politica, conformidad]
status: draft
owner: human:jisequilla
stale_after: 2027-10-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
sources:
  - id: estandar
    resource: /references/okf-standard.md
    title: Estándar OKF, perfil knowledge/2.0
---

# Ámbito

`knowledge/` de este repo, `examples/knowledge`, y cualquier bundle generado por los scripts.

# Norma

- DEBE existir `index.md` con `okf_version`, `log.md` y `project.md` (`type: Project`).[^estandar]
- DEBE llevar `generated: { by, at }` todo concepto (en bundles 0.1, `timestamp`).
- NO DEBE escribirse `verified` con actor `human:` por un agente.
- NO DEBE mezclarse forma 0.1 y 0.2 en un bundle.
- DEBERÍA tener `description` todo concepto y `stale_after` todo runbook, métrica y política.

# Verificación / controles

`make lint` en CI; `okf-capture` termina siempre con lint.

[^estandar]: Estándar OKF, perfil knowledge/2.0
