---
type: Runbook
title: Actualizar la spec OKF desde el upstream de Google
description: Qué hacer cuando GoogleCloudPlatform/knowledge-catalog publica cambios en okf/SPEC.md.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [runbook, spec, compatibilidad]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Disparador

Nueva versión en `okf/SPEC.md` upstream (revisar trimestralmente o al ver `stale_after` vencido en este runbook).

# Pasos

1. Descargar `SPEC.md` y compararlo con `okf-standard/references/OKF-SPEC-v<actual>.md`.
2. Clasificar cambios: aditivos (nuevos campos opcionales) vs rompedores (renombrados, reservados).
3. Actualizar `references/` (copia literal + licencia), `OKF-COMPATIBILIDAD.md` (matriz) y, si procede, `SUPPORTED_VERSIONS`, `V02_KEYS`/detección y `okf_migrate.py`.
4. Añadir fixture upstream de la nueva versión en `examples/fixtures/` y caso en `make test`.
5. ADR nuevo si cambia la política de versiones ([ADR-0004](/decisiones/ADR-0004-soporte-dual-v01-v02.md)).
6. Seguir [Publicar una versión](/runbooks/publicar-version.md).
