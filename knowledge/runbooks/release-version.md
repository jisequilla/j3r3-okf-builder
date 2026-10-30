---
type: Runbook
title: Publicar una versión del plugin
description: Pasos para liberar una versión nueva de okf-builder en todas las plataformas.
tags: [runbook, release]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Disparador

Cambio en skills, scripts, plantillas o estándar que deba llegar a usuarios.

# Pasos

1. Actualizar `version` en `plugin/okf-builder/.claude-plugin/plugin.json` y en `.claude-plugin/marketplace.json` (semver).
2. Si cambió una decisión: ADR nuevo con `okf-capture`; registrar en `knowledge/log.md`.
3. `make all` → `test`, `plugin`, `copilot`, `m365`. Debe terminar en `OK`.
4. `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json` y `.claude-plugin/marketplace.json`.
5. `make lint` (knowledge/ propio y ejemplo a 0 errores).
6. Commit + tag `v<version>` + push. Claude Code: `/plugin marketplace update`.
7. Entregar proyecciones: ver [Exportar proyecciones](/runbooks/export-projections.md).

# Rollback

Revertir el tag y volver a publicar la versión anterior; los bundles de usuarios no cambian con la versión del plugin.
