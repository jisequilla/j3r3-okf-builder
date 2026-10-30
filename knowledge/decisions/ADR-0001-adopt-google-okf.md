---
type: Architecture Decision
title: "ADR-0001: Adoptar el Open Knowledge Format de Google como base del estándar"
description: El conocimiento de proyecto se representa como bundle OKF (markdown + frontmatter YAML) en lugar de un formato propio.
tags: [adr, estandar]
status: stable
adr_id: ADR-0001
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

Se necesitaba una estructura estándar de conocimiento reutilizable entre proyectos y consumible por agentes. Las opciones eran un formato propio, un vault Obsidian con convenciones, o adoptar OKF (publicado por Google en junio de 2026, formaliza el patrón LLM-wiki).

# Decisión

Adoptamos OKF como base y definimos encima un **perfil** (`knowledge/1.0`) con lo que OKF deja abierto: directorios, vocabulario de tipos y campos obligatorios adicionales. Ver [Política de conformidad](/policies/okf-conformance.md).

# Alternativas consideradas

| Alternativa | Pros | Contras | Motivo de descarte |
|---|---|---|---|
| Formato propio | Control total | Sin interoperabilidad; hay que escribir todos los consumidores | OKF cubre el 90 % con un estándar abierto |
| Vault Obsidian | Tooling maduro | Convenciones no especificadas; wikilinks no estándar | OKF es markdown estándar y ya interopera con Knowledge Catalog |

# Consecuencias

- Positivas: interoperable con cualquier indexador markdown y con Google Knowledge Catalog; versionable en git; sin runtime.
- Negativas: dependencia de la evolución de la spec (v0.1→v0.2 ya trajo dos cambios rompedores); mitigado en [ADR-0004](/decisions/ADR-0004-dual-support-v01-v02.md).
