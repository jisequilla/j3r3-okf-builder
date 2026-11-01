---
type: Architecture Decision
title: "ADR-0016: Distillation adds refutation: an outdated concept is deprecated without opening a conflict"
description: Fragments keep the KDD format and one Conflict Log per bundle; distillation classifies each item as an addition, confirmation, update, refutation or conflict, where a refutation proposes deprecating a concept and naming its replacement, and only disputed items open a conflict.
tags: [adr, standard, capture]
status: draft
adr_id: ADR-0016
decision_status: accepted
supersedes: /decisions/ADR-0015-fragment-format-and-conflict-log.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T12:00:00Z }
sources:
  - { id: kdd-distill, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/playbooks/destilado.md", title: "KDD bundle: distillation playbook (añade, confirma, refuta, conflicto)" }
  - { id: kdd-check, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/playbooks/doble-check.md", title: "KDD bundle: double-check playbook" }
  - { id: review, resource: /fragments/2026-10-31-kdd-bundle-review.md, title: "Fragment: review of the KDD profiles bundle" }
  - { id: kdd-structure, resource: "https://github.com/jisequilla/kdd-knowledge/blob/48eaa13/knowledge/architecture/estructura-del-repositorio.md", title: "KDD bundle: directories, custom types and fields" }
---

# Context

[ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md) adopted the KDD bundle's fragment format and conflict register[^review][^kdd-structure], but gave distillation four kinds of item: addition, confirmation, update and conflict. The KDD bundle has a fifth, *refuta*: when a fragment clearly makes a concept outdated, the distiller proposes deprecating it and naming its replacement, without a row in the conflict register. Only a real disagreement becomes a *conflicto*[^kdd-distill]. Under ADR-0015 every outdated concept opened a conflict. That fills the register with items nobody disputes, and the register stops showing what is actually open.

The owner chose to add refutation here and leave the KDD bundle as it is. As with ADR-0015, the bundle in use is the evidence.

# Decision

1. **A fragment is a concept of type `Knowledge Fragment`** in `fragments/`, named `YYYY-MM-DD-slug.md` with the date of the event; the slug may carry the origin and a sequence number when one event yields several fragments (`2026-10-31-conv-01-roles.md`). Besides the required fields it carries:
   - `occurred_at`: when the event happened, not when it was captured;
   - `origin`: where it happened (a meeting, a chat, slides, a transcript);
   - `participants`: who took part, as actors;
   - `distillation_status`: `pending`, `distilled` or `conflict` (while one of its conflicts is open).
2. **The body has two sections.** `# Record` holds the event as it happened, edited only to remove secrets and personal data the participants did not agree to keep; a transcript keeps its speaker labels and timestamps. `# Distillation` lists each proposed item with its kind, outcome and the concept it touched. Bundles written in Spanish may title them «Contenido capturado» and «Destilado en».
3. **The record is immutable.** After capture only `distillation_status` and `# Distillation` change; a wrong record is deprecated and replaced.
4. **Text records are copied in; other originals stay outside the bundle.** A text record that exists elsewhere is copied into `# Record` and its location kept in `sources`. Slides, recordings and other files stay in their own system or in a `/sources` folder at the repository root, outside `knowledge/`, and are cited in `sources`.
5. **Three skills** do the work: `okf-fragment` captures a fragment; `okf-distill` reads one fragment and the concepts it touches and proposes a change set; `okf-review` is the double check: it shows the changes since the last review, the open conflicts and the concepts awaiting human verification. Nothing is applied until a person approves the change set.
6. **Each item of a change set has one of five kinds:**

   | Kind | When | Proposed change |
   |---|---|---|
   | *Addition* | The fragment brings knowledge the bundle lacks | A new concept, or a new part of one |
   | *Confirmation* | The fragment states what a concept already says | The fragment is added to the concept's `sources` |
   | *Update* | The fragment refines a concept and contradicts nothing | The concept is edited, with an **Update** log entry |
   | *Refutation* | The fragment makes a concept outdated and names or implies its replacement, and nobody in the record disputes it | The concept is deprecated and links to its replacement (for an ADR, a new ADR that supersedes it); a **Deprecation** log entry; no conflict is opened |
   | *Conflict* | The fragment contradicts a concept and it is unclear which is right: participants disagree, sources disagree, or the replacement is not known | A row in the conflict register |

   When in doubt between refutation and conflict, the item is a conflict.
7. **Every concept created, confirmed, updated or deprecated from a fragment cites it** in `sources` with a bundle path (`resource: /fragments/...`) and footnotes on the claims it supports.
8. **Each bundle keeps one conflict register**, a concept of type `Conflict Log`, at `/conflict-log.md` unless the bundle places it elsewhere. Each row has an ID (`C-NNN`), the source fragment, a description, the kind of conflict, the resolution, a state (`open`, `proposed`, `resolved`, `dismissed`) and who decided. The register is created with the first conflict. A conflict is never resolved by overwriting: the knowledge changed (a decision becomes a new ADR that supersedes the old one; anything else is updated with an **Update** entry citing the fragment, or deprecated as in a refutation), or it was a misunderstanding and is dismissed with the reason. Opening and resolving a conflict is logged with the label **Conflict**.
9. **Distillation never sets `verified`.** Approving a change set is not reviewing a concept; `verified: human:` stays a separate, explicit act.
10. **The Microsoft 365 agent of [ADR-0013](/decisions/ADR-0013-agent-projections.md) leaves out `okf-migrate`**, so the three skills fit within its limit of 8.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0015: every contradiction is a conflict | Four kinds; one path for anything that contradicts | The register fills with undisputed replacements; it no longer shows what is open | The KDD bundle already separates the two, and its register stays readable |
| The KDD bundle drops *refuta* and adopts ADR-0015 | No change here | The KDD playbook, role and agent change, and the human-verified role needs re-verification | The owner kept the KDD bundle as it is |
| Refutation deletes or rewrites the old concept | Shorter bundle | Breaks links and history | Never delete; deprecate and link to the replacement |

# Consequences

- Positive: the conflict register holds only disputed items; the plugin and the KDD bundle classify distillation the same way, so the functional-architect and knowledge-architect agents share one vocabulary.
- Negative / accepted debt: the line between refutation and conflict is a judgment, made by the distiller and checked when a person approves the change set; the rule "when in doubt, conflict" keeps the error on the safe side.
- Follow-up actions: those of ADR-0015, unchanged, plus the five kinds in `okf-distill` and in the distillation row of `OKF-STANDARD.md`.

# Related

* [ADR-0005: generated required and verified only by people](/decisions/ADR-0005-required-generated-human-verified.md)
* [ADR-0013: Agent projections](/decisions/ADR-0013-agent-projections.md)
* [ADR-0015: Knowledge fragments follow the KDD bundle's format, and conflicts go to one register](/decisions/ADR-0015-fragment-format-and-conflict-log.md)
* [Conflict log](/conflict-log.md)
* [Knowledge architect](/roles/knowledge-architect.md)

[^kdd-distill]: KDD bundle, distillation playbook; the double-check playbook resolves a conflict as a misunderstanding, a refutation or a real divergence between domains.
[^review]: Fragment of 2026-10-31, review of the KDD profiles bundle.
[^kdd-structure]: KDD bundle, directories, custom types and fields.
