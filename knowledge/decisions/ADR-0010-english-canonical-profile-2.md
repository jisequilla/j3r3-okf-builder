---
type: Architecture Decision
title: "ADR-0010: English as the repo's canonical language and profile knowledge/2.0"
description: The profile vocabulary, the code, the skills and the repo's knowledge move to English, with a fixed glossary; the vocabulary change bumps the profile to knowledge/2.0.
tags: [adr, structure, language]
status: draft
adr_id: ADR-0010
decision_status: accepted
supersedes: /decisions/ADR-0003-spanish-names.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

[ADR-0003](/decisions/ADR-0003-spanish-names.md) set directories and types in Spanish because the first audience worked in Spanish. The repo is now public and addresses users on several platforms, most of whom do not read Spanish. Google's spec and its example bundles use English (`Metric`, `Policy`, `metrics/`, `policies/`, log entries `**Creation**`), so the Spanish profile forced consumers to tolerate two vocabularies. No external bundle uses profile `knowledge/1.0` yet.

# Decision

1. **English is the canonical language** of the profile vocabulary, the scripts and their output, the skills, the templates, the documentation and `knowledge/`. Agents still answer in the language of whoever writes to them; a `README.es.md` summarizes the project in Spanish.
2. **The profile moves to `knowledge/2.0`**, because the directories, the `type` values and the `decision_status` values change. No es→en migration is written: there are no bundles to migrate.
3. **ADRs are translated**, including their file slugs, without changing any decision: the translation is not a decision change, and this ADR records it. Internal links are rewritten with the new names.
4. **Canonical glossary** of the migration, mandatory in every ticket:

| Scope | Spanish | English |
|---|---|---|
| Directory | `arquitectura/` · `decisiones/` · `dominio/` · `sistemas/` · `datos/` · `metricas/` · `computaciones/` · `politicas/` | `architecture/` · `decisions/` · `domain/` · `systems/` · `data/` · `metrics/` · `computations/` · `policies/` |
| `type` | `Proyecto` · `Vista de Arquitectura` · `Decisión de Arquitectura` · `Término` · `Glosario` · `Sistema` · `Tabla` · `Métrica` · `Política` · `Referencia` | `Project` · `Architecture View` · `Architecture Decision` · `Term` · `Glossary` · `System` · `Table` · `Metric` · `Policy` · `Reference` |
| `decision_status` | `propuesta` · `aceptada` · `sustituida` · `rechazada` | `proposed` · `accepted` · `superseded` · `rejected` |
| `log.md` entry | `Creación` · `Actualización` · `Deprecación` · `Inicialización` · `Migración` · `Verificación` | `Creation` · `Update` · `Deprecation` · `Initialization` · `Migration` · `Verification` |
| Fixed file | `proyecto.md` | `project.md` |
| Linter output | `CONFORMANTE` · `conceptos` · `errores` · `avisos` | `CONFORMANT` · `concepts` · `errors` · `warnings` |

Unchanged: `apis/`, `runbooks/`, `playbooks/`, `references/`, `skills/`, `attesters/` and the types `API`, `Dataset`, `Runbook`, `Playbook`, `Attested Computation` and `Log`. `data/` is used rather than Google's `tables/`, because the directory holds both `Dataset` and `Table`.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep Spanish (ADR-0003) | No work | Excludes most users; the vocabulary diverges from upstream | The repo is now public |
| Bilingual profile (configurable vocabulary) | Both audiences served | Duplicates the vocabulary in the linter, indexes and templates | Complexity without demand: agents already answer in Spanish |
| Redefine `knowledge/1.0` in English | No version change | A `1.0` with two meanings | Honest semver costs only a string |
| Keep the Spanish slugs | Fewer renames | Spanish file names in an English repo | The broken-link lint verifies the renames |

# Consequences

- Positive: the vocabulary matches Google's spec and examples; users on any platform can read the repo; the debt that ADR-0003 accepted disappears.
- Negative / accepted debt: about 150 files have to be translated; `knowledge/1.0` bundles (none known) are left without automatic migration.
- Follow-up actions: the migration is built following [Build a change in layers](/runbooks/build-in-layers.md): layer 1, the profile vocabulary in scripts, templates and the standard; layer 2, the scripts' output; layer 3, the prose of skills, documentation and `knowledge/`.

# Related

* [ADR-0003: Profile directories and types in Spanish](/decisions/ADR-0003-spanish-names.md) (superseded)
* [ADR-0009: Build in layers and tickets](/decisions/ADR-0009-build-in-layers-and-tickets.md)
* [Knowledge profile](/domain/knowledge-profile.md)
