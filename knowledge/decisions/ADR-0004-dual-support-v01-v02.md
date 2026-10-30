---
type: Architecture Decision
title: "ADR-0004: Soportar OKF v0.1 y v0.2 con v0.2 por defecto"
description: El perfil escribe v0.2, lee y valida v0.1, y migra en ambos sentidos sin mezclar formas en un bundle.
tags: [adr, compatibilidad]
status: stable
adr_id: ADR-0004
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

v0.2 (jul-2026) introdujo dos cambios rompedores respecto a v0.1: `timestamp` → `generated` y `# Citations` → `sources[]`. Existen bundles v0.1 publicados y consumidores que solo entienden v0.1. Detalle en [OKF-COMPATIBILITY](/references/okf-compatibility.md).

# Decisión

- Nuevo bundle ⇒ v0.2. `okf-init --okf-version 0.1` solo para interoperar con consumidores antiguos.
- Versión de un bundle = `okf_version` del `index.md` raíz; si falta, heurística por campos.
- Nunca mezclar formas; `okf-lint` lo marca (`MIXED_VERSIONS`).
- Capturar en la versión del bundle, no en la preferida.
- Degradar a 0.1 solo a una copia (`okf-migrate --to 0.1 --out`); la fuente se queda en 0.2.

# Consecuencias

- Positivas: se pueden consumir los bundles de Google v0.1 y exportar a consumidores antiguos sin perder la fuente.
- Negativas: el linter y el migrador tienen dos modos que mantener; cubierto por `make test` con fixtures reales de ambas versiones.
