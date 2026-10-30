---
type: Architecture Decision
title: "ADR-0010: Inglés como idioma canónico del repo y perfil knowledge/2.0"
description: El vocabulario del perfil, el código, los skills y el conocimiento del repo pasan a inglés, con un glosario fijo; el cambio de vocabulario sube el perfil a knowledge/2.0.
tags: [adr, estructura, idioma]
status: draft
adr_id: ADR-0010
decision_status: accepted
supersedes: /decisions/ADR-0003-spanish-names.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T19:31:49Z }
---

# Contexto

[ADR-0003](/decisions/ADR-0003-spanish-names.md) fijó directorios y tipos en español porque el primer público trabajaba en español. El repo ahora es público y se dirige a usuarios de varias plataformas, y la mayoría no lee español. La spec de Google y sus bundles de ejemplo usan inglés (`Metric`, `Policy`, `metrics/`, `policies/`, entradas de log `**Creation**`), así que el perfil en español obligaba a los consumidores a tolerar dos vocabularios. Ningún bundle externo usa todavía el perfil `knowledge/1.0`.

# Decisión

1. **El inglés es el idioma canónico** del vocabulario del perfil, los scripts y su salida, los skills, las plantillas, la documentación y `knowledge/`. Los agentes siguen respondiendo en el idioma de quien les escribe; un `README.es.md` resume el proyecto en español.
2. **El perfil pasa a `knowledge/2.0`**, porque cambian los directorios, los valores de `type` y los de `decision_status`. No se escribe una migración es→en: no hay bundles que migrar.
3. **Los ADRs se traducen**, incluidos sus slugs de fichero, sin cambiar ninguna decisión: la traducción no es un cambio de decisión, y este ADR la registra. Los enlaces internos se reescriben con los nombres nuevos.
4. **Glosario canónico** de la migración, de uso obligatorio en todos los tickets:

| Ámbito | Español | Inglés |
|---|---|---|
| Directorio | `arquitectura/` · `decisiones/` · `dominio/` · `sistemas/` · `datos/` · `metricas/` · `computaciones/` · `politicas/` | `architecture/` · `decisions/` · `domain/` · `systems/` · `data/` · `metrics/` · `computations/` · `policies/` |
| `type` | `Proyecto` · `Vista de Arquitectura` · `Decisión de Arquitectura` · `Término` · `Glosario` · `Sistema` · `Tabla` · `Métrica` · `Política` · `Referencia` | `Project` · `Architecture View` · `Architecture Decision` · `Term` · `Glossary` · `System` · `Table` · `Metric` · `Policy` · `Reference` |
| `decision_status` | `propuesta` · `aceptada` · `sustituida` · `rechazada` | `proposed` · `accepted` · `superseded` · `rejected` |
| Entrada de `log.md` | `Creación` · `Actualización` · `Deprecación` · `Inicialización` | `Creation` · `Update` · `Deprecation` · `Initialization` |
| Fichero fijo | `proyecto.md` | `project.md` |
| Salida del linter | `CONFORMANTE` · `conceptos` · `errores` · `avisos` | `CONFORMANT` · `concepts` · `errors` · `warnings` |

No cambian: `apis/`, `runbooks/`, `playbooks/`, `references/`, `skills/`, `attesters/` y los tipos `API`, `Dataset`, `Runbook`, `Playbook`, `Attested Computation` y `Log`. Se usa `data/` y no el `tables/` de Google, porque el directorio contiene tanto `Dataset` como `Table`.

# Alternativas consideradas

| Alternativa | Pros | Contras | Motivo de descarte |
|---|---|---|---|
| Mantener el español (ADR-0003) | Sin trabajo | Excluye a la mayoría de usuarios; el vocabulario diverge del upstream | El repo ahora es público |
| Perfil bilingüe (vocabulario configurable) | Ambos públicos servidos | Duplica el vocabulario en linter, índices y plantillas | Complejidad sin demanda: los agentes ya responden en español |
| Redefinir `knowledge/1.0` en inglés | Sin cambio de versión | Un `1.0` con dos significados | Semver honesto cuesta solo una cadena |
| Conservar los slugs en español | Menos renombres | Nombres de fichero en español en un repo en inglés | El lint de enlaces rotos verifica los renombres |

# Consecuencias

- Positivas: el vocabulario coincide con la spec y los ejemplos de Google; los usuarios de cualquier plataforma pueden leer el repo; desaparece la deuda que ADR-0003 aceptaba.
- Negativas / deuda asumida: hay que traducir unos 150 ficheros; los bundles `knowledge/1.0` (ninguno conocido) quedan sin migración automática.
- Acciones derivadas: la migración se construye según [Construir un cambio por capas](/runbooks/build-in-layers.md): capa 1, vocabulario del perfil en scripts, plantillas y estándar; capa 2, salida de los scripts; capa 3, prosa de skills, documentación y `knowledge/`.

# Relacionados

* [ADR-0003: Directorios y tipos del perfil en español](/decisions/ADR-0003-spanish-names.md) (sustituido)
* [ADR-0009: Construir por capas y tickets](/decisions/ADR-0009-build-in-layers-and-tickets.md)
* [Perfil knowledge](/domain/knowledge-profile.md)
