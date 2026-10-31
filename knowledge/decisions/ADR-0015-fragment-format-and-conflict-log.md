---
type: Architecture Decision
title: "ADR-0015: Knowledge fragments follow the KDD bundle's format, and conflicts go to one register"
description: A fragment is a Knowledge Fragment with occurred_at, origin, participants and distillation_status; each bundle keeps one Conflict Log; okf-fragment, okf-distill and okf-review are separate skills, and distillation still needs a person's approval.
tags: [adr, standard, capture]
status: draft
adr_id: ADR-0015
decision_status: accepted
supersedes: /decisions/ADR-0012-knowledge-fragments-and-distillation.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T19:45:00Z }
sources:
  - { id: review, resource: /fragments/2026-10-31-kdd-bundle-review.md, title: "Fragment: review of the KDD profiles bundle" }
  - { id: kdd-structure, resource: "https://github.com/jisequilla/kdd-knowledge/blob/48eaa13/knowledge/architecture/estructura-del-repositorio.md", title: "KDD bundle: directories, custom types and fields" }
  - { id: spec-terms, resource: /references/okf-spec-google.md, title: "OKF v0.2 §2 and §3: every .md other than index.md and log.md is a concept" }
---

# Context

[ADR-0012](/decisions/ADR-0012-knowledge-fragments-and-distillation.md) introduced fragments and distillation before any bundle used them. The KDD profiles bundle, built with this plugin, then captured 21 fragments, distilled them and closed 7 conflicts with a person deciding each one[^kdd-structure]. Its format differs from ADR-0012 in the type name, the fields, the place of conflicts and the skills it expects. The owner reviewed both and chose a format for the plugin to build[^review]. The fragment format is also the contract with the functional-architect agent, so it has to match what that bundle already uses.

# Decision

1. **A fragment is a concept of type `Knowledge Fragment`** in `fragments/`, named `YYYY-MM-DD-slug.md` with the date of the event; the slug may carry the origin and a sequence number when one event yields several fragments (`2026-10-31-conv-01-roles.md`). Besides the required fields it carries:
   - `occurred_at`: when the event happened, not when it was captured;
   - `origin`: where it happened (a meeting, a chat, slides, a transcript);
   - `participants`: who took part, as actors (§7);
   - `distillation_status`: `pending`, `distilled` or `conflict` (while one of its conflicts is open).
2. **The body has two sections.** `# Record` holds the event as it happened, edited only to remove secrets and personal data the participants did not agree to keep; a transcript keeps its speaker labels and timestamps. `# Distillation` lists each proposed item with its kind, outcome and the concept it touched. Bundles written in Spanish may title them «Contenido capturado» and «Destilado en».
3. **The record is immutable.** After capture only `distillation_status` and `# Distillation` change; a wrong record is deprecated and replaced.
4. **Text records are copied in; other originals stay outside the bundle.** A text record that exists elsewhere is copied into `# Record` and its location kept in `sources`. Slides, recordings and other files stay in their own system or in a `/sources` folder at the repository root, outside `knowledge/`, and are cited in `sources`.
5. **Three skills** do the work: `okf-fragment` captures a fragment; `okf-distill` reads one fragment and the concepts it touches and proposes a change set, each item an *addition*, a *confirmation* (the fragment becomes a source of an existing concept), an *update* that contradicts nothing, or a *conflict*; `okf-review` is the double check: it shows the changes since the last review, the open conflicts and the concepts awaiting human verification. Nothing is applied until a person approves the change set.
6. **Every concept created, confirmed or updated from a fragment cites it** in `sources` with a bundle path (`resource: /fragments/...`) and footnotes on the claims it supports.
7. **Each bundle keeps one conflict register**, a concept of type `Conflict Log`, at `/conflict-log.md` unless the bundle places it elsewhere. Each row has an ID (`C-NNN`), the source fragment, a description, the kind of conflict, the resolution, a state (`open`, `proposed`, `resolved`, `dismissed`) and who decided. The register is created with the first conflict. A conflict is never resolved by overwriting: the knowledge changed (a decision becomes a new ADR that supersedes the old one; anything else is updated with an **Update** entry citing the fragment), or it was a misunderstanding and is dismissed with the reason. Opening and resolving a conflict is logged with the label **Conflict**.
8. **Distillation never sets `verified`.** Approving a change set is not reviewing a concept; `verified: human:` stays a separate, explicit act.
9. **The Microsoft 365 agent of [ADR-0013](/decisions/ADR-0013-agent-projections.md) leaves out `okf-migrate`**, so the three skills fit within its limit of 8.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0012 as accepted and migrate the KDD bundle | No new ADR | 21 fragments and a working conflict register rewritten to a format nobody used yet | The bundle in use is the better evidence |
| Adopt the KDD format without `participants` | Nothing to add to that bundle | A record without who took part cannot be checked against the people | `participants` is cheap and the review needs it |
| Conflicts in each fragment (ADR-0012) | No extra concept | No single view of what is open; a conflict spanning fragments has no home | The register already worked in the KDD bundle |
| Fold fragment capture into `okf-capture` and the review into `okf-distill` | 7 skills, one spare M365 slot | Each skill does two jobs, and the KDD agents name three | The owner chose separate skills and dropping `okf-migrate` from M365 |

# Consequences

- Positive: the plugin builds the format a real bundle already uses; one place shows every open conflict; the functional-architect agent and the knowledge-architect agent share one contract.
- Negative / accepted debt: the M365 agent has no slot left and no migration skill; two profile types (`Knowledge Fragment`, `Conflict Log`) and one more log label; Spanish section titles are accepted next to the English ones.
- Follow-up actions: the layered build of ADR-0012's follow-ups, now under this decision: both types, the fields and the **Conflict** label in `OKF-STANDARD.md` (both copies) and `okf_lint`; `fragment.md` and `conflict-log.md` templates; the `okf-fragment`, `okf-distill` and `okf-review` skills; the `okf-ask` rule that ranks distilled concepts above fragments; `okf_migrate` for the new fields.

# Related

* [ADR-0005: generated required and verified only by people](/decisions/ADR-0005-required-generated-human-verified.md)
* [ADR-0012: Knowledge fragments and distillation](/decisions/ADR-0012-knowledge-fragments-and-distillation.md)
* [ADR-0013: Agent projections](/decisions/ADR-0013-agent-projections.md)
* [Conflict log](/conflict-log.md)

[^review]: Fragment of 2026-10-31, review of the KDD profiles bundle.
[^kdd-structure]: KDD bundle, directories, custom types and fields.
