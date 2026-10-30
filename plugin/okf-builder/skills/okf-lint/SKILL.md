---
name: okf-lint
description: Valida que knowledge/ cumple la spec OKF v0.2 y el perfil knowledge/1.0 (frontmatter, type, index/log, actores, ISO 8601, enlaces, caducidad, índices desactualizados). Usar cuando el usuario diga "valida el conocimiento", "okf lint", "comprueba el bundle", "¿está bien formado knowledge/?", o antes de un commit/PR que toque knowledge/.
---

# okf-lint

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

## Pasos

1. Ejecutar:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_lint.py" [<bundle>] [--json] [--strict] [--no-profile] [--okf-version auto|0.1|0.2]
   ```
   Sin argumento busca `knowledge/` hacia arriba desde el cwd. `--no-profile` valida solo la spec (útil para bundles externos). `--okf-version auto` (defecto) usa `okf_version` del `index.md` raíz o la infiere; la última línea de salida indica `OKF <versión> (<origen>)`.
2. Interpretar la salida:
   - `ERROR` rompe la conformidad (sin frontmatter, sin `type`, YAML inválido, `status` inválido, `index`/`log` mal formados, faltan `index.md`/`log.md`/`proyecto.md`, falta `generated`, Attested Computation sin `runtime`/computación).
   - `WARN` es guía: enlaces rotos (`BROKEN_LINK`), `STALE`, `INDEX_STALE`, sin `description`, actores o fechas mal formadas, nombres no kebab-case.
   - Versiones: `LEGACY_TIMESTAMP`/`LEGACY_CITATIONS` (formas 0.1 en bundle 0.2), `V02_FIELD_IN_V01` (claves 0.2 en bundle 0.1, se preservan), `MIXED_VERSIONS` (a medio migrar), `NO_OKF_VERSION` (raíz sin declarar versión), `VERSION_MISMATCH`. Todas se resuelven con `okf-migrate` o declarando `okf_version`.
3. Proponer correcciones concretas por fichero. Para `INDEX_STALE` ejecutar `okf-index`. Para `STALE` listar los conceptos y pedir al usuario decisión: renovar `stale_after`, actualizar contenido o deprecar. Para `BROKEN_LINK` ofrecer `okf-capture` del concepto que falta.
4. Si el usuario lo pide, aplicar las correcciones mecánicas (formato de fechas, `status`, regenerar índices) y volver a ejecutar hasta 0 errores. No tocar contenido semántico ni `verified` sin confirmación.
5. Para integrarlo en CI, proponer:
   ```yaml
   # .github/workflows/okf-lint.yml
   - run: python3 tools/okf/okf_lint.py knowledge --strict
   ```
   copiando `scripts/okf_common.py` y `okf_lint.py` a `tools/okf/` del repo (sin dependencias).
