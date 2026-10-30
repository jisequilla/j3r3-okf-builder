---
type: System
title: Scripts OKF
description: okf_init, okf_lint, okf_index y okf_migrate (Python ≥ 3.9, sin dependencias) en okf-standard/scripts.
resource: /plugin/okf-builder/skills/okf-standard/scripts
tags: [sistema, scripts, python]
status: draft
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Responsabilidad

| Script | Función | Salida |
|---|---|---|
| okf_init.py | Scaffold de `knowledge/` (v0.2 o v0.1) | ficheros; regenera índices |
| okf_lint.py | Conformidad spec (§11) + perfil; detección de versión | hallazgos ERROR/WARN, `--json`, exit code |
| okf_index.py | Regenera `index.md` por directorio desde frontmatter | `--check` para CI |
| okf_migrate.py | 0.1 ↔ 0.2, `--dry-run`, `--out`, `--keep-extensions`, `--file` | ficheros + entrada en log.md |
| okf_common.py | Parser YAML reducido, modelo Doc, detección de versión | librería |

# Examples

```bash
python3 <skills>/okf-standard/scripts/okf_lint.py knowledge --strict
python3 <skills>/okf-standard/scripts/okf_migrate.py knowledge --to 0.2 --dry-run
```

# Operación

* Pruebas: `make test` (init 0.1/0.2, fixtures de Google v0.1 y v0.2, round-trip de migración).
* Decisiones: [ADR-0006](/decisions/ADR-0006-dependency-free-scripts.md), [ADR-0004](/decisions/ADR-0004-dual-support-v01-v02.md).
