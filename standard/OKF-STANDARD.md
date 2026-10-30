# Estándar OKF para proyectos (perfil `knowledge/`)

**Versión del perfil:** 2.0 · **Base:** Open Knowledge Format (OKF) v0.2 de Google ·
**Spec de referencia:** https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf

Este documento define cómo se organiza el conocimiento de un proyecto dentro de su propio repositorio, en una carpeta `knowledge/`, de forma que sea un *bundle* OKF conformante y consumible por personas y agentes (Claude Code, Cowork, Knowledge Catalog, cualquier indexador markdown).

---

## 1. Principios

1. **Un repo, un bundle.** `knowledge/` es la raíz del bundle. Su ruta es la identidad de cada concepto.
2. **Solo markdown + frontmatter YAML.** Sin SDK, sin runtime. `cat` es suficiente para leerlo; `git` para distribuirlo.
3. **`type` es el único campo obligatorio.** Todo lo demás es recomendado, nunca motivo de rechazo.
4. **Divulgación progresiva.** Cada directorio tiene un `index.md`; un agente empieza por la raíz y desciende solo donde necesita.
5. **Trazabilidad primero.** Todo concepto generado por un agente lleva `generated`; todo concepto revisado por una persona lleva `verified` con actor `human:`.
6. **El grafo lo forman los enlaces.** Las relaciones (depende-de, se-une-con, sustituye-a) se expresan con enlaces markdown y prosa, no con campos especiales.

---

## 2. Estructura de directorios

```
knowledge/
├── index.md                 # Raíz del bundle. Único index.md con frontmatter (okf_version).
├── log.md                   # Historial cronológico del bundle (más reciente primero).
├── project.md               # type: Project — ficha del proyecto: propósito, alcance, equipo, enlaces clave.
├── architecture/            # Vistas, contexto C4, diagramas, principios.
│   ├── index.md
│   └── vision-general.md
├── decisions/               # ADRs (Architecture Decision Records).
│   ├── index.md
│   └── ADR-0001-....md
├── domain/                  # Glosario y conceptos de negocio.
│   ├── index.md
│   └── glosario.md
├── systems/                 # Componentes, servicios, módulos desplegables.
│   └── index.md
├── apis/                    # Contratos de API (referencian OpenAPI/Proto, no los sustituyen).
│   └── index.md
├── data/                    # Datasets, tablas, esquemas, rutas de join.
│   └── index.md
├── metrics/                 # Definiciones de métricas/KPIs; enlazan a computaciones atestadas.
│   └── index.md
├── computations/            # type: Attested Computation (SQL/dbt/python sancionado).
│   └── index.md
├── runbooks/                # Operación: incidentes, despliegues, rollback.
│   └── index.md
├── playbooks/               # Procedimientos de negocio/equipo (onboarding, releases).
│   └── index.md
├── policies/                # Normas, estándares, compliance, seguridad.
│   └── index.md
└── references/              # Convención OKF §6.3: material externo espejado, skills de ejecución, attesters.
    ├── index.md
    ├── skills/
    └── attesters/
```

**Reglas:**

- Todos los subdirectorios son **opcionales** salvo `index.md`, `log.md` y `project.md` en la raíz. `okf-init` los crea todos vacíos (solo con su `index.md`) para que la navegación sea predecible entre proyectos; se eliminan los que no apliquen.
- Los nombres de directorio del perfil están en español salvo `references/`, que mantiene el nombre de la spec para interoperar con consumidores OKF.
- Nombres de fichero: `kebab-case`, ASCII, sin espacios. ADRs: `ADR-NNNN-titulo-corto.md`.
- `index.md` y `log.md` son **nombres reservados** en cualquier nivel: nunca se usan para un concepto.
- Un proyecto puede añadir directorios propios (p. ej. `integraciones/`, `seguridad/`). Se documentan en el `index.md` raíz.

---

## 3. Documento de concepto

Todo fichero `.md` no reservado es un **concepto**: frontmatter YAML + cuerpo markdown.

### 3.1 Frontmatter

```yaml
---
type: Runbook                              # OBLIGATORIO
title: Respuesta a alerta de frescura      # recomendado
description: Pasos para triar una alerta de frescura del pipeline de pedidos.  # recomendado, una frase
resource: https://grafana.acme/d/abc       # URI del activo subyacente, si existe
tags: [oncall, incidentes, pedidos]        # recomendado
status: stable                             # draft | stable | deprecated (ausente ⇒ stable)
stale_after: 2027-06-30T00:00:00Z          # instante absoluto a partir del cual el contenido es obsoleto
generated: { by: human:jisequilla, at: 2026-10-30T16:00:00Z }
verified:
  - { by: human:jisequilla, at: 2026-10-30T16:00:00Z }
sources:
  - id: sre-handbook
    resource: https://wiki.acme/sre/handbook
    title: Manual SRE
    author: team:sre
    last_modified: 2026-09-01T00:00:00Z
---
```

| Campo | Obligatorio | Regla del perfil |
|---|---|---|
| `type` | **Sí** | Usar el vocabulario de §4. Tipos nuevos permitidos si son autoexplicativos. |
| `title` | Recomendado | Si falta, el consumidor deriva del nombre de fichero. |
| `description` | Recomendado | Una frase. Es lo que aparece en `index.md`. |
| `resource` | Si aplica | URI canónica del activo (repo, dashboard, tabla, endpoint). |
| `tags` | Recomendado | Lista YAML, minúsculas, kebab-case. |
| `status` | Recomendado | `draft` al crear; `stable` tras revisión; `deprecated` nunca se borra, se enlaza al sustituto. |
| `stale_after` | Recomendado en runbooks, métricas, políticas | ISO 8601 con offset explícito. |
| `generated` | **Obligatorio en el perfil** | `{ by: <actor>, at: <ISO 8601> }`. Quién/qué escribió el contenido actual. |
| `verified` | Recomendado | Lista de `{ by, at }`. Un mapa simple se interpreta como lista de un elemento. |
| `sources` | Recomendado si el contenido deriva de algo | Cada entrada con `resource` obligatorio; `id` si el cuerpo lo cita con nota al pie `[^id]`. |

**Convención de actores (§7 de la spec):** `human:<id>` para personas, `process:<id>` para procesos automáticos, `<productor>/<versión>` para agentes (p. ej. `okf-builder/claude-fable-5-1`). El prefijo `human:` es lo que eleva el nivel de confianza a *human-reviewed*.

**Niveles de confianza derivados:** sin `verified` ⇒ *unverified*; `verified` solo por no-humanos ⇒ *machine-confirmed*; algún `human:` ⇒ *human-reviewed*.

### 3.2 Cuerpo

Markdown estructurado (encabezados, listas, tablas, bloques de código) antes que prosa libre. Encabezados con significado convencional:

| Encabezado | Uso |
|---|---|
| `# Schema` | Columnas/campos de un activo de datos (tabla con Columna / Tipo / Descripción). |
| `# Examples` | Ejemplos de uso en bloques de código. |
| `# Computation` | Único bloque de código con la computación sancionada (solo `type: Attested Computation`). |

Los encabezados del resto de plantillas (§5) son recomendaciones del perfil, no de la spec.

### 3.3 Enlaces

- Forma recomendada: **absoluta respecto al bundle**, empezando por `/`: `[pedidos](/data/pedidos.md)`.
- Relativa permitida: `[vecino](./otro.md)`.
- Un enlace roto **no** es un error de conformidad: representa conocimiento aún no escrito. `okf-lint` lo reporta como aviso.
- Atribución por afirmación: nota al pie cuya etiqueta es un `sources[].id`: `...se particiona por día.[^ga4-schema]`.

---

## 4. Vocabulario de tipos del perfil

| `type` | Directorio habitual | Descripción |
|---|---|---|
| `Project` | raíz | Ficha del proyecto. Exactamente uno por bundle (`project.md`). |
| `Architecture View` | `architecture/` | Contexto, contenedores, componentes, despliegue, principios. |
| `Architecture Decision` | `decisions/` | ADR. Campos extra: `adr_id`, `decision_status` (proposed/accepted/superseded/rejected), `supersedes`, `superseded_by`. |
| `Term` / `Glossary` | `domain/` | Un término de negocio, o el glosario agregado. |
| `System` | `systems/` | Servicio, módulo, job, componente desplegable. Campos extra: `owner`, `repo`, `runtime`. |
| `API` | `apis/` | Contrato; `resource` apunta al OpenAPI/Proto/AsyncAPI. |
| `Dataset` / `Table` | `data/` | Activo de datos. Cuerpo con `# Schema` y `# Joins`. |
| `Metric` | `metrics/` | Definición de negocio; enlaza a su `Attested Computation`. |
| `Attested Computation` | `computations/` | Nombre fijado por la spec (§10). Requiere `runtime`. |
| `Runbook` | `runbooks/` | Procedimiento operativo: Disparador, Diagnóstico, Pasos, Rollback, Escalado. |
| `Playbook` | `playbooks/` | Procedimiento de equipo/negocio. |
| `Policy` | `policies/` | Norma o estándar; suele llevar `stale_after` y `verified` humano. |
| `Reference` | `references/` | Material externo espejado o instrucciones de ejecución. |
| `Log` | — | Solo para `log.md` si se le añade frontmatter (opcional, tolerado por consumidores). |

Los tipos no se registran centralmente; los consumidores deben tolerar tipos desconocidos.

---

## 5. Ficheros reservados

### 5.1 `index.md`

- Uno por directorio. Sin frontmatter, **excepto** el de la raíz, que lleva `okf_version: "0.2"` y, en este perfil, `okf_profile: "knowledge/2.0"`.
- Cuerpo: secciones con encabezado `#` y lista de enlaces `* [Título](ruta) - descripción`. La descripción se copia del `description` del concepto.
- El `index.md` raíz lista subdirectorios y conceptos de raíz. `okf-index` lo regenera; las secciones manuales que empiecen por `# Notas` se preservan.

```markdown
---
okf_version: "0.2"
okf_profile: "knowledge/2.0"
---

# Project

* [Ficha del proyecto](project.md) - Propósito, alcance y enlaces clave del proyecto.

# Subdirectories

* [architecture](architecture/index.md) - Architecture views and principles.
* [decisions](decisions/index.md) - Architecture decision records (ADR).
```

### 5.2 `log.md`

- Al menos en la raíz. Lista plana agrupada por fecha ISO `YYYY-MM-DD`, **más reciente primero**.
- Cada entrada empieza por una palabra en negrita: `**Creation**`, `**Update**`, `**Verification**`, `**Deprecation**`, `**Initialization**`.

```markdown
# Historial del bundle

## 2026-10-30
* **Initialization**: Estructura `knowledge/` creada con el perfil knowledge/2.0.
```

---

## 6. Ciclo de vida del conocimiento

| Evento | Acción | Frontmatter |
|---|---|---|
| Crear concepto | `okf-capture` con plantilla | `status: draft`, `generated` con el actor que lo escribe |
| Revisión humana | Persona lee y aprueba | `status: stable`, añadir `verified: { by: human:<id>, at }` |
| Cambio de contenido | Editar | Actualizar `generated.at`; `verified` **no** se toca (puede quedar anterior a `generated.at`, eso es información) |
| Reconfirmar sin cambios | Revisión periódica | Añadir nueva entrada a `verified` |
| Caducidad | `now >= stale_after` | `okf-lint` avisa; revisar y renovar `stale_after` o deprecar |
| Sustitución | Nuevo concepto | Antiguo: `status: deprecated` + enlace al nuevo. Nunca borrar: se rompe el grafo y el historial |
| Cualquiera de los anteriores | Registrar | Entrada en `log.md` del directorio afectado y/o raíz |

---

## 7. Conformidad

Un bundle `knowledge/` es **conformante OKF v0.2** si:

1. Todo `.md` no reservado tiene un bloque frontmatter YAML parseable.
2. Todo frontmatter tiene `type` no vacío.
3. `index.md` y `log.md`, cuando existen, siguen §5.

Es **conformante con este perfil** si, además:

4. Existen `knowledge/index.md` (con `okf_version`), `knowledge/log.md` y `knowledge/project.md` (`type: Project`).
5. Todo concepto lleva `generated.by` con la convención de actores.
6. Los timestamps son ISO 8601 con offset explícito.
7. `status`, si aparece, es `draft | stable | deprecated`.
8. Los `Attested Computation` llevan `runtime` y, o bien `computation`, o bien un bloque `# Computation` con un único fence.
9. Los nombres de fichero son kebab-case ASCII.

`okf-lint` distingue **errores** (1–5, 7, 8) de **avisos** (6, 9, enlaces rotos, `stale_after` vencido, conceptos sin `description`, `index.md` desactualizado).

---

## 8. Consumo por agentes (Claude Code / Cowork)

1. Leer `knowledge/index.md` → identificar directorios relevantes a la pregunta.
2. Leer el `index.md` del directorio → elegir conceptos por `description`.
3. Abrir conceptos; seguir enlaces solo si la pregunta lo requiere.
4. Al responder, citar la ruta del concepto y su nivel de confianza (`verified`, `status`, `stale_after`).
5. Si la respuesta descubre conocimiento que falta o está mal, proponer una captura (`okf-capture`) en lugar de dejarlo en el chat.

Recomendación: añadir en el `CLAUDE.md` del repo una línea del tipo
`El conocimiento del proyecto está en knowledge/ (formato OKF). Empieza por knowledge/index.md.`

---

## 9. Versiones OKF soportadas

El perfil es **v0.2 por defecto** y trabaja con **v0.1** en lectura, validación, captura y migración bidireccional. Los dos cambios rompedores entre versiones son `timestamp` → `generated: { by, at }` y `# Citations` (cuerpo) → `sources[]` (frontmatter); todo lo demás de v0.2 es aditivo y opcional. La versión de un bundle se toma de `okf_version` en el `index.md` raíz y, si falta, se infiere de los campos presentes. Detalle completo, matriz de campos y reglas de mapeo en `OKF-COMPATIBILITY.md`.

Reglas operativas:

- Nunca mezclar formas 0.1 y 0.2 en un mismo bundle; `okf-lint` lo marca como `MIXED_VERSIONS`.
- Al capturar, escribir en la versión del bundle, no en la preferida.
- Para intercambiar con un consumidor 0.1 estricto, exportar una copia degradada (`okf-migrate --to 0.1 --keep-extensions`); el bundle fuente se mantiene en 0.2.

## 10. Referencias

- Spec OKF v0.2: `SPEC.md` en https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf (v0.1: mismo fichero en el commit `ee67a5c`)
- Compatibilidad v0.1 ↔ v0.2: `OKF-COMPATIBILITY.md`
- Anuncio: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- Patrón LLM-wiki (Karpathy): https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
