# Compatibilidad OKF v0.1 ↔ v0.2

**Fuentes:** `SPEC.md` v0.1 (commit `ee67a5c`, jun-2026) y v0.2 (commit `780fe9d`, jul-2026, + `62432a0` ago-2026 que exige offset explícito en todos los timestamps) del repo `GoogleCloudPlatform/knowledge-catalog`. Copias literales en `plugin/okf-builder/skills/okf-standard/references/`.

Google declara v0.2 como *minor bump* salvo **dos cambios rompedores** (§13.1). En la práctica un consumidor v0.2 lee v0.1 con dos fallbacks, y un consumidor v0.1 lee v0.2 porque debe tolerar claves desconocidas. El perfil `knowledge/1.0` es **v0.2 por defecto** y soporta v0.1 en modo lectura, validación y migración en ambos sentidos.

---

## 1. Lo que NO cambia (núcleo común)

| Elemento | v0.1 | v0.2 |
|---|---|---|
| Bundle = árbol de markdown | ✓ | ✓ |
| Ficheros reservados `index.md`, `log.md` | ✓ | ✓ |
| `index.md` sin frontmatter salvo raíz con `okf_version` | ✓ | ✓ |
| `log.md`: `## YYYY-MM-DD`, más reciente primero | ✓ | ✓ |
| `type` único campo obligatorio | ✓ | ✓ |
| `title`, `description`, `resource`, `tags` recomendados | ✓ | ✓ |
| Enlaces absolutos al bundle `/dir/x.md` o relativos | ✓ | ✓ |
| Enlaces rotos tolerados | ✓ | ✓ |
| Encabezados `# Schema`, `# Examples` | ✓ | ✓ |
| Tipos no registrados; claves desconocidas preservadas | ✓ | ✓ |
| Conformidad: frontmatter parseable + `type` + reservados bien formados | ✓ (§9) | ✓ (§11) |
| Convención `references/` | ✓ (en §8 Citations) | ✓ (§6.3) |

Cualquier herramienta que solo use el núcleo común trabaja con ambas versiones sin cambios.

---

## 2. Cambios rompedores (§13.1)

| # | v0.1 | v0.2 | Mapeo 0.1→0.2 | Mapeo 0.2→0.1 |
|---|---|---|---|---|
| B1 | `timestamp: <ISO>` (frontmatter) — última modificación | `generated: { by: <actor>, at: <ISO> }` | `generated.at = timestamp`; `generated.by` **no existe en 0.1** → se asigna un actor por defecto (`process:okf-migrate`) o el que indique el usuario | `timestamp = generated.at`; `generated.by` se pierde (opcionalmente conservar `generated` como extensión) |
| B2 | Sección de cuerpo `# Citations` con lista `[n] [título](url)` (spec) o `- url` / `- [título](url)` (bundles reales) | Frontmatter `sources: [{ id, resource, title, author, usage_count, last_modified }]` + notas al pie `[^id]` | Cada cita → `sources[]` con `resource=url`, `title` si lo hay, `id=cit-n`; referencias `[n]` en el cuerpo → `[^cit-n]`; eliminar la sección `# Citations` | Cada `sources[]` → línea `[n] [title](resource)` bajo `# Citations`; `[^id]` → `[n]`; eliminar definiciones de nota al pie; señales (`author`, `usage_count`, `last_modified`) se pierden salvo que se conserven como extensión |

Fallbacks que la spec v0.2 autoriza al consumidor: leer `timestamp` si falta `generated` (MAY) y parsear `# Citations` (MAY). `okf-lint` en modo 0.2 los reporta como `LEGACY_TIMESTAMP` / `LEGACY_CITATIONS` (aviso, no error).

---

## 3. Añadidos de v0.2 (solo opcionales; su ausencia ⇒ concepto v0.1 plano)

| Familia | Claves | Semántica | En un bundle v0.1 |
|---|---|---|---|
| Procedencia | `sources[]`, `usage_window` | De qué deriva el concepto; señales de credibilidad por fuente | Desconocidas → se preservan, no se interpretan |
| Confianza | `generated`, `verified[]` | Quién escribió / quién confirmó. Niveles: unverified / machine-confirmed / human-reviewed | Ídem |
| Ciclo de vida | `status` (`draft\|stable\|deprecated`), `stale_after` | Estado y caducidad absoluta | Ídem |
| Actores | `human:<id>`, `process:<id>`, `<agente>/<versión>` | Convención para `generated.by`, `verified[].by`, `sources[].author` | No existe |
| Computación atestada | `type: Attested Computation`, `runtime`, `parameters`, `computation`, `executor`, `attester`, heading `# Computation` | Cálculo sancionado y verificable | Tipo desconocido → concepto genérico |
| Timestamps | Todo datetime con **offset explícito** (`Z` o `±hh:mm`) desde `62432a0` | — | v0.1 solo pedía ISO 8601 |

Diferencias menores de redacción: v0.1 dice que los consumidores *SHOULD NOT* rechazar claves desconocidas; v0.2 lo eleva a *MUST NOT*. v0.1 tenía una sección "Relationship to other formats" (eliminada en v0.2). v0.2 añade "Non-goal: empaquetado del código de executor/attester".

---

## 4. Detección de versión

Orden de precedencia que aplica `okf_common.detect_version()`:

1. `okf_version` en el frontmatter del `index.md` raíz → autoritativo.
2. Heurística sobre los conceptos:
   - Algún concepto con `generated`, `verified`, `sources`, `status`, `stale_after` o `type: Attested Computation` ⇒ **0.2**.
   - Si no, algún concepto con `timestamp` o sección `# Citations` ⇒ **0.1**.
   - Si no hay señales (solo núcleo común) ⇒ **0.2** (indistinguible; se trata como la versión actual).
3. Mezcla de señales 0.1 y 0.2 sin `okf_version` ⇒ **0.2 con aviso `MIXED_VERSIONS`** (bundle a medio migrar).

---

## 5. Política del perfil `knowledge/1.0`

| Situación | Comportamiento |
|---|---|
| Bundle nuevo (`okf-init`) | v0.2. `--okf-version 0.1` genera la forma 0.1 (`timestamp`, sin `generated`) para proyectos que deban interoperar con consumidores antiguos. |
| Validar (`okf-lint`) | `--okf-version auto\|0.1\|0.2`. En 0.1: `timestamp` y `# Citations` son correctos; claves v0.2 se reportan como `V02_FIELD_IN_V01` (aviso informativo). En 0.2: `timestamp`/`# Citations` ⇒ `LEGACY_*`. El perfil knowledge (exige `generated`) solo se aplica en 0.2; en 0.1 el equivalente exigido es `timestamp`. |
| Consultar (`okf-ask`) | Transparente: la antigüedad se lee de `generated.at` o, en su defecto, `timestamp`; las fuentes de `sources[]` o, en su defecto, `# Citations`. Sin `verified` (siempre en 0.1) ⇒ "sin verificar". |
| Capturar (`okf-capture`) | Escribe en la versión detectada del bundle. Nunca mezcla: si el bundle es 0.1, usa `timestamp` y `# Citations`. |
| Migrar (`okf-migrate`) | `--to 0.2` (recomendado, sin pérdida) o `--to 0.1` (con pérdida: `generated.by`, `verified`, `status`, `stale_after`, señales de fuentes; con `--keep-extensions` se conservan como claves extra, legal en ambas specs). Siempre `--dry-run` disponible; actualiza `okf_version` y añade entrada en `log.md`. |
| Intercambio con terceros | Publicar en 0.2. Si el consumidor es 0.1 estricto, exportar con `okf-migrate --to 0.1 --keep-extensions` a un directorio aparte; no degradar el bundle fuente. |

---

## 6. Matriz de campos (referencia rápida)

| Clave | 0.1 | 0.2 | Nota |
|---|---|---|---|
| `type` | REQ | REQ | — |
| `title` `description` `resource` `tags` | REC | REC | — |
| `timestamp` | REC | ✗ (legacy) | → `generated.at` |
| `generated.by` | ✗ | REQ dentro de `generated` | sin equivalente en 0.1 |
| `generated.at` | ✗ | REC | ← `timestamp` |
| `verified[]` | ✗ | OPT | se pierde al bajar |
| `status` | ✗ | OPT (default `stable`) | se pierde al bajar |
| `stale_after` | ✗ | OPT | se pierde al bajar |
| `sources[]` | ✗ | OPT | ↔ `# Citations` |
| `usage_window` | ✗ | OPT | se pierde al bajar |
| `runtime` `parameters` `computation` `executor` `attester` | ✗ | REQ/OPT en Attested Computation | tipo pasa a genérico en 0.1 |
| `okf_version` (index raíz) | `"0.1"` | `"0.2"` | — |
| `# Citations` (cuerpo) | REC | ✗ (legacy) | ↔ `sources[]` |
| `# Computation` (cuerpo) | ✗ | CONV | — |
| `[^id]` notas al pie | ✗ | CONV | ↔ `[n]` |
