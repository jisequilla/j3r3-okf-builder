# okf-builder

Plugin de Claude Code / Cowork para gestionar el conocimiento de un proyecto como **bundle OKF** (Open Knowledge Format v0.2, Google) dentro de `knowledge/` en cada repositorio.

## Skills

| Skill | Qué hace |
|---|---|
| `okf-standard` | Conocimiento del estándar y del perfil `knowledge/1.0`; plantillas de conceptos. |
| `okf-init` | Crea la estructura `knowledge/` en el repo actual. |
| `okf-capture` | Añade un concepto (ADR, runbook, sistema, API, tabla, métrica, término, política…) con plantilla, log e índice. |
| `okf-lint` | Valida conformidad con la spec y el perfil. |
| `okf-index` | Regenera los `index.md` desde el frontmatter. |
| `okf-ask` | Responde preguntas del proyecto navegando el bundle y citando fuentes y confianza. |
| `okf-migrate` | Detecta la versión OKF y migra 0.1 ↔ 0.2 (con `--out` para exportar copias degradadas). |

## Scripts (sin dependencias; Python ≥ 3.9)

En `skills/okf-standard/scripts/` (los skills los referencian como `<skills>/okf-standard/scripts/`):

```
okf_init.py   --root . --title "…" --description "…" --actor human:<id>
okf_lint.py   [knowledge] [--json] [--strict] [--no-profile]
okf_index.py  [knowledge] [--check] [--dir sub]
okf_migrate.py [knowledge] --to 0.2|0.1 [--actor A] [--keep-extensions] [--out DIR] [--dry-run] [--file rel.md]
```

Copiables a `tools/okf/` de cualquier repo para CI.

## Estándar

`skills/okf-standard/references/OKF-ESTANDAR.md` define el perfil; `OKF-COMPATIBILIDAD.md` la matriz v0.1↔v0.2. Specs originales en `references/OKF-SPEC-v0.1.md` y `OKF-SPEC-v0.2.md` (Apache-2.0, GoogleCloudPlatform/knowledge-catalog).
