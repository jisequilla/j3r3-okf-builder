---
type: Knowledge Fragment
title: "2026-10-31 · Review of the KDD profiles bundle against the okf-builder ADRs"
description: The owner's decisions after comparing the KDD profiles bundle, built with the plugin, with ADR-0012, ADR-0013 and ADR-0014 on fragments, conflicts, skills and where the bundle lives.
tags: [fragment, kdd, review]
status: draft
occurred_at: 2026-10-31
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T19:45:00Z }
sources:
  - { id: kdd-bundle, resource: "https://github.com/jisequilla/kdd-knowledge/tree/48eaa13/knowledge", title: "KDD profiles bundle (private repository), commit 48eaa13" }
  - { id: kdd-structure, resource: "https://github.com/jisequilla/kdd-knowledge/blob/48eaa13/knowledge/architecture/estructura-del-repositorio.md", title: "KDD bundle: directories, custom types and fields" }
  - { id: kdd-conflicts, resource: "https://github.com/jisequilla/kdd-knowledge/blob/48eaa13/knowledge/analysis/registro-de-conflictos.md", title: "KDD bundle: conflict register" }
  - { id: kdd-plugin, resource: "https://github.com/jisequilla/kdd-knowledge/blob/48eaa13/knowledge/systems/plugin-okf-builder.md", title: "KDD bundle: capabilities it expects from okf-builder" }
---

# Record

**What was compared.** The KDD profiles bundle (93 concepts, `okf_lint --strict` 0 errors) defines, among its own types[^kdd-structure]:

| KDD bundle | okf-builder ADR-0012 |
|---|---|
| type `Knowledge Fragment`, file `YYYY-MM-DD-<origin>-NN-<topic>.md` | type `Fragment`, file `YYYY-MM-DD-slug.md` |
| `occurred_at`, `origin`, `distillation_status` (`pending` · `distilled` · `conflict`) | `occurred_at`, `medium`, `participants` |
| sections «Contenido capturado» and «Destilado en»; raw sources outside the bundle in `/sources` | `# Record` and `# Distillation`; the record copied into the fragment |
| one conflict register, IDs `C-NNN`, states abierto · propuesto · resuelto · descartado, who decided[^kdd-conflicts] | conflicts listed in each fragment and logged with `**Conflict**` |
| skills `okf-fragment`, `okf-distill`, `okf-review` (double check)[^kdd-plugin] | fragment step in `okf-capture`, plus `okf-distill` |

**Questions put to the owner and the answers, verbatim.**

- *Which fragment format should we build?* — "Merge both (Recommended)": keep their name and fields (`Knowledge Fragment`, `origin`, `distillation_status`) and add our `participants`.
- *Where are conflicts recorded?* — "Central register (Recommended)".
- *With `okf-fragment`, `okf-distill` and `okf-review` separate, the agent would carry 9 skills and M365 allows 8. How do we fit?* — "Separate, drop one": `okf-migrate` stays out of the M365 agent.
- *Where should the KDD knowledge live?* — "One KDD monorepo (Recommended)", separate from okf-builder.
- *How does a contributor without Git work?* — first "Claude + zip, you commit"; later in the session the contributor got a GitHub account and joined as a collaborator, working with GitHub Desktop and Claude Cowork.
- *Repository names?* — "Neutral names (Recommended)".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Fragment type, fields, file name and sections | conflict with ADR-0012 | applied: new ADR supersedes it | [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md), [C-001](/conflict-log.md) |
| One conflict register per bundle | conflict with ADR-0012 | applied | [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md), [C-002](/conflict-log.md) |
| `okf-fragment`, `okf-distill`, `okf-review` as separate skills | conflict with ADR-0012 | applied | [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md), [C-003](/conflict-log.md) |
| M365 agent leaves out `okf-migrate` | update of ADR-0013's skill list, within its 8-skill cap | applied | [ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md) |
| KDD knowledge in its own monorepo; neutral repository names | addition | pending: outside this bundle's scope, tracked as work items | — |

[^kdd-structure]: KDD bundle, directories, custom types and fields.
[^kdd-conflicts]: KDD bundle, conflict register.
[^kdd-plugin]: KDD bundle, capabilities expected from okf-builder.
