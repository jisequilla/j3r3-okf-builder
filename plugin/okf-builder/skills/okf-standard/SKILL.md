---
name: okf-standard
description: Conocimiento del estándar OKF (Open Knowledge Format v0.1 y v0.2 de Google), sus diferencias, y del perfil knowledge/2.0 para repos. Cárgalo cuando el usuario pregunte qué es OKF, cómo estructurar knowledge/, qué campos lleva el frontmatter, qué type usar, cómo escribir un ADR/runbook/métrica en OKF, o cuando otro skill okf-* necesite la spec. Triggers: "OKF", "open knowledge format", "estructura de conocimiento", "knowledge/", "frontmatter OKF", "bundle OKF", "plantilla ADR OKF", "OKF 0.1 vs 0.2", "versión de OKF".
---

# Estándar OKF · perfil knowledge/2.0

Este skill es la fuente de verdad del estándar dentro del plugin. Los demás skills (`okf-init`, `okf-capture`, `okf-lint`, `okf-index`, `okf-ask`) lo asumen.

## Resumen operativo (lo que hay que recordar siempre)

- Un bundle = directorio `knowledge/` en la raíz del repo. Solo markdown + frontmatter YAML.
- Fichero reservados: `index.md` (listado por directorio, sin frontmatter salvo la raíz con `okf_version`) y `log.md` (historial, fechas `## YYYY-MM-DD`, más reciente primero).
- Todo `.md` no reservado es un **concepto**. Único campo obligatorio: `type`.
- Perfil knowledge/2.0 añade como obligatorio: `generated: { by: <actor>, at: <ISO 8601> }` y la existencia de `index.md`, `log.md` y `project.md` (`type: Project`).
- Actores: `human:<id>` · `process:<id>` · `<agente>/<version>`. Cuando este plugin escribe contenido, usa `okf-builder/<modelo>` como actor en `generated.by`; **nunca** inventar `verified` con `human:`: solo la persona lo añade.
- Enlaces entre conceptos: absolutos al bundle `[x](/systems/x.md)`. Enlaces rotos = conocimiento pendiente, no error.
- Lifecycle: `status: draft|stable|deprecated` (ausente ⇒ stable), `stale_after` instante absoluto. Nunca borrar: deprecar y enlazar al sustituto.
- Procedencia: `sources[]` con `resource` obligatorio e `id` si el cuerpo cita con `[^id]`.

## Estructura de directorios del perfil

```
knowledge/
  index.md  log.md  project.md
  architecture/  decisions/  domain/  systems/  apis/  data/
  metrics/  computations/  runbooks/  playbooks/  policies/  references/
```

Todos los subdirectorios son opcionales; cada uno lleva su `index.md`.

## Vocabulario de `type` → directorio → plantilla

| type | directorio | plantilla |
|---|---|---|
| Project | raíz | `<skills>/okf-standard/templates/project.md` |
| Architecture View | architecture/ | `<skills>/okf-standard/templates/architecture-view.md` |
| Architecture Decision | decisions/ (`ADR-NNNN-slug.md`) | `<skills>/okf-standard/templates/adr.md` |
| Term / Glossary | domain/ | `<skills>/okf-standard/templates/term.md` |
| System | systems/ | `<skills>/okf-standard/templates/system.md` |
| API | apis/ | `<skills>/okf-standard/templates/api.md` |
| Table / Dataset | data/ | `<skills>/okf-standard/templates/table.md` |
| Metric | metrics/ | `<skills>/okf-standard/templates/metric.md` |
| Attested Computation | computations/ | `<skills>/okf-standard/templates/computation.md` |
| Runbook | runbooks/ | `<skills>/okf-standard/templates/runbook.md` |
| Playbook | playbooks/ | `<skills>/okf-standard/templates/playbook.md` |
| Policy | policies/ | `<skills>/okf-standard/templates/policy.md` |
| Reference | references/ | `<skills>/okf-standard/templates/reference.md` |

Las plantillas usan marcadores `{{name}}`; sustituir todos antes de guardar. Si un marcador no aplica, eliminar la línea, no dejarlo vacío.

## Versiones: v0.2 (por defecto) y v0.1

- Un bundle es **0.1** si su `index.md` raíz declara `okf_version: "0.1"` o si sus conceptos usan `timestamp` / `# Citations` sin ninguna clave 0.2. Es **0.2** en el resto de casos.
- Dos cambios rompedores: `timestamp` → `generated: { by, at }` y `# Citations` (cuerpo, `[n] [título](url)` o `- url`) → `sources[]` (frontmatter) + notas al pie `[^id]`. Todo lo demás de 0.2 (`verified`, `status`, `stale_after`, actores, Attested Computation, offset obligatorio en fechas) es aditivo.
- **Escribir siempre en la versión del bundle.** En un bundle 0.1: `timestamp` en vez de `generated`, citas bajo `# Citations`, sin `status`/`verified`/`stale_after`. Las plantillas son 0.2; para un bundle 0.1 rellenar la plantilla y pasar `okf_migrate.py --to 0.1 --file <ruta>`.
- Un consumidor 0.2 lee 0.1 (fallback a `timestamp` y `# Citations`); un consumidor 0.1 lee 0.2 ignorando claves desconocidas. Nunca mezclar formas en un mismo bundle.
- Matriz completa, reglas de mapeo y política de intercambio: `references/OKF-COMPATIBILITY.md`. Migración: skill `okf-migrate`.

## Dónde está todo (convención `<skills>`)

`<skills>` = directorio que contiene los skills `okf-*` (el padre de este skill). Este skill lleva los scripts y las plantillas que usan los demás:

```
<skills>/okf-standard/scripts/okf_init.py | okf_lint.py | okf_index.py | okf_migrate.py | okf_common.py
<skills>/okf-standard/templates/*.md
<skills>/okf-standard/references/OKF-STANDARD.md | OKF-COMPATIBILITY.md | OKF-SPEC-v0.1.md | OKF-SPEC-v0.2.md
```

Python ≥ 3.9, sin dependencias. Si el entorno no permite ejecutar scripts (p. ej. algunos agentes M365), aplicar las reglas manualmente desde `references/` y decirlo.

## Cuándo leer las referencias

- Dudas de detalle del perfil (reglas de nombres, ciclo de vida, conformidad): leer `references/OKF-STANDARD.md`.
- Dudas de la spec (sources, verified, Attested Computation, conformidad §11): leer `references/OKF-SPEC-v0.2.md`; para bundles antiguos, `references/OKF-SPEC-v0.1.md`. Copias literales de la spec de Google, licencia en `references/OKF-SPEC-LICENSE.md`.
- Diferencias entre versiones y mapeo de campos: `references/OKF-COMPATIBILITY.md`.

## Reglas de redacción de conceptos

1. `description`: una frase, sin punto final redundante, útil fuera de contexto (aparece en índices y buscadores).
2. Cuerpo estructurado: tablas y listas antes que prosa. Encabezados `# Schema`, `# Examples`, `# Computation` tienen significado convencional.
3. Un concepto = una unidad de conocimiento. Si un documento cubre tres métricas, son tres conceptos enlazados desde uno narrativo.
4. Citar fuentes externas con `sources[]` + nota al pie; no copiar texto externo literal.
5. Al crear o modificar: entrada en `log.md` (raíz y, si existe, del directorio) y regenerar `index.md` (`okf-index`).
