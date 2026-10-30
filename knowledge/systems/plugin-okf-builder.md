---
type: System
title: Plugin okf-builder
description: Paquete de 7 skills Agent Skills (okf-standard, init, capture, lint, index, ask, migrate) que aplican el perfil knowledge/2.0.
resource: /plugin/okf-builder
tags: [sistema, plugin, skills]
status: draft
owner: human:jisequilla
runtime: agent-skills
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Responsabilidad

Dar a cualquier agente las instrucciones para crear, mantener, validar, consultar y migrar bundles OKF. No ejecuta nada por sí mismo: delega en [los scripts](/systems/scripts-okf.md).

# Interfaces

| Skill | Disparadores típicos | Usa |
|---|---|---|
| okf-standard | "qué es OKF", "qué type uso", "0.1 vs 0.2" | references/, templates/ |
| okf-init | "inicializa OKF", "crea knowledge" | okf_init.py |
| okf-capture | "documenta esta decisión", "crea un runbook" | templates, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-lint | "valida knowledge" | okf_lint.py |
| okf-index | "regenera índices" | okf_index.py |
| okf-ask | "¿por qué decidimos…?" | lectura progresiva de index.md |
| okf-migrate | "migra a 0.2", "exporta para 0.1" | okf_migrate.py |

# Dependencias

* [Scripts OKF](/systems/scripts-okf.md)
* Manifest: `plugin/okf-builder/.claude-plugin/plugin.json` (versión semver; `marketplace.json` en la raíz del repo).

# Operación

* Runbooks: [Publicar una versión](/runbooks/release-version.md)
* Validación: `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json`
