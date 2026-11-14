---
type: Standard Decision
title: "SDR-0017: A fragment's record is immutable, and a missing capture field may be backfilled once from the record itself"
description: Fragments keep the KDD format, one Conflict Log per bundle and five kinds of distillation item; after capture the record never changes, but a missing occurred_at, origin or participants may be filled once, with a value read from the record or from an original its sources cite, approved by a person and logged.
tags: [adr, standard, capture]
status: stable
decision_id: SDR-0017
formerly: ADR-0024
decision_status: accepted
supersedes: /base/decisions/standard/SDR-0010-refutation-as-a-distillation-kind.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: { by: human:jisequilla, at: 2026-11-08T13:48:10Z }
sources:
  - { id: adr-0016, resource: /base/decisions/standard/SDR-0010-refutation-as-a-distillation-kind.md }
  - { id: adr-0005, resource: /base/decisions/standard/SDR-0005-required-generated-human-verified.md }
  - { id: adr-0017, resource: /base/decisions/architecture/ADR-0017-agent-skills-per-platform.md }
---

# Context

[ADR-0016](/base/decisions/standard/SDR-0010-refutation-as-a-distillation-kind.md) fixed the fragment format, the five kinds of distillation item and the Conflict Log, and made the record immutable: "After capture only `distillation_status` and `# Distillation` change"[^adr-0016]. That rule covers the frontmatter as well as `# Record`.

The capture fields `occurred_at`, `origin` and `participants` arrived after bundles had started capturing fragments. The KDD bundle has 22 fragments captured before `participants` existed, and `okf_lint` warns `FRAGMENT_NO_FIELD` on each of them. In most of them the record shows who took part, in attendee lines or speaker labels, so the value can be read, not guessed. Under ADR-0016 the warning can never be cleared, and the field stays empty even where the record holds its answer.

The immutability rule protects what happened: the record is evidence, and editing it rewrites the evidence. Filling a missing field from the record adds no claim the record does not already make. Changing a value already written, or filling one from memory, does add one. The owner chose to allow the first and keep forbidding the second.

ADR-0016's decision 10, the subset of skills of the Microsoft 365 agent, has been governed by [ADR-0017](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md) and `tools/m365-agent.json` since that ADR[^adr-0017]; it is not restated here.

# Decision

1. **A fragment is a concept of type `Knowledge Fragment`** in `fragments/`, named `YYYY-MM-DD-slug.md` with the date of the event; the slug may carry the origin and a sequence number when one event yields several fragments (`2026-10-31-conv-01-roles.md`). Besides the required fields it carries:
   - `occurred_at`: when the event happened, not when it was captured;
   - `origin`: where it happened (a meeting, a chat, slides, a transcript);
   - `participants`: who took part, as actors;
   - `distillation_status`: `pending`, `distilled` or `conflict` (while one of its conflicts is open).
2. **The body has two sections.** `# Record` holds the event as it happened, edited only to remove secrets and personal data the participants did not agree to keep; a transcript keeps its speaker labels and timestamps. `# Distillation` lists each proposed item with its kind, outcome and the concept it touched. Bundles written in Spanish may title them «Contenido capturado» and «Destilado en».
3. **The record is immutable.** After capture, `distillation_status` and `# Distillation` change as distillation proceeds; `# Record` and every other key never change, with one exception, the backfill of decision 4. A wrong record is deprecated and replaced.
4. **A missing capture field may be backfilled once.** When a fragment lacks `occurred_at`, `origin` or `participants`, the field may be added:
   - only if it is absent; a value already written is never changed, and a wrong one is handled by deprecating the fragment and replacing it;
   - only with a value read from the fragment's own `# Record` or from an original its `sources` already cite (a dated invite, attendee lines, speaker labels), never inferred or remembered; `participants` lists the actors the record shows taking part;
   - only after a person approves it, the mapping of names to actor ids included; the backfill is proposed as a change set, as in distillation;
   - with `# Record`, `generated` and every other key left untouched: `generated` keeps naming who captured the record, and the backfill is recorded in the log;
   - with an **Update** entry in `log.md` naming the fragments, the fields filled and who approved them.

   A fragment whose record does not show the value keeps the field absent, and lint keeps warning.
5. **Text records are copied in; other originals stay outside the bundle.** A text record that exists elsewhere is copied into `# Record` and its location kept in `sources`. Slides, recordings and other files stay in their own system or in a `/sources` folder at the repository root, outside `knowledge/`, and are cited in `sources`.
6. **Three skills** do the work: `okf-fragment` captures a fragment and proposes backfills; `okf-distill` reads one fragment and the concepts it touches and proposes a change set; `okf-review` is the double check: it shows the changes since the last review, the open conflicts and the concepts awaiting human verification. Nothing is applied until a person approves the change set.
7. **Each item of a change set has one of five kinds:**

   | Kind | When | Proposed change |
   |---|---|---|
   | *Addition* | The fragment brings knowledge the bundle lacks | A new concept, or a new part of one |
   | *Confirmation* | The fragment states what a concept already says | The fragment is added to the concept's `sources` |
   | *Update* | The fragment refines a concept and contradicts nothing | The concept is edited, with an **Update** log entry |
   | *Refutation* | The fragment makes a concept outdated and names or implies its replacement, and nobody in the record disputes it | The concept is deprecated and links to its replacement (for an ADR, a new ADR that supersedes it); a **Deprecation** log entry; no conflict is opened |
   | *Conflict* | The fragment contradicts a concept and it is unclear which is right: participants disagree, sources disagree, or the replacement is not known | A row in the conflict register |

   When in doubt between refutation and conflict, the item is a conflict.
8. **Every concept created, confirmed, updated or deprecated from a fragment cites it** in `sources` with a bundle path (`resource: /fragments/...`) and footnotes on the claims it supports.
9. **Each bundle keeps one conflict register**, a concept of type `Conflict Log`, at `/conflict-log.md` unless the bundle places it elsewhere. Each row has an ID (`C-NNN`), the source fragment, a description, the kind of conflict, the resolution, a state (`open`, `proposed`, `resolved`, `dismissed`) and who decided. The register is created with the first conflict. A conflict is never resolved by overwriting: the knowledge changed (a decision becomes a new ADR that supersedes the old one; anything else is updated with an **Update** entry citing the fragment, or deprecated as in a refutation), or it was a misunderstanding and is dismissed with the reason. Opening and resolving a conflict is logged with the label **Conflict**.
10. **Neither distillation nor a backfill sets `verified`.** Approving a change set is not reviewing a concept; `verified: human:` stays a separate, explicit act[^adr-0005].

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0016: no change after capture | The simplest rule; nothing to judge | A field the record answers stays empty for good, and the warning never clears | The record already holds the value; filling it adds no claim |
| New fragments only; old ones keep the warning | No exception to the rule | The same as above, and a bundle's warnings stop telling real gaps from old ones | Same reason |
| Allow any edit of the frontmatter after capture | Flexible | A frontmatter edit can change what the record says happened (a date, a participant) | Only absent fields, only from the record |
| Fill from memory or from other fragments | Fills more fields | Adds claims the record does not make; nobody can check them against the fragment | The record is the evidence |
| Record each backfill in the fragment itself | Visible in the file | Adds a key that is history; dated history belongs in `log.md` | The log already records changes |

# Consequences

- Positive: old fragments can reach the current format where their record allows it; lint warnings on fragments mean a value is unknown, not that it predates the field; the record stays the only evidence for every capture field.
- Negative / accepted debt: a backfill is a judgment (does the record really show who took part?), checked when a person approves it; `generated` no longer dates every byte of a fragment's frontmatter, and the log does.
- Follow-up actions: say in both copies of `OKF-STANDARD.md` (§4, the `Knowledge Fragment` row) that a missing capture field may be backfilled; a backfill step in `okf-fragment` (find fragments missing a capture field, read the value from the record, propose the change set, log it); tell the KDD bundle's session, whose question led to this decision.

# Related

* [ADR-0005: generated required and verified only by people](/base/decisions/standard/SDR-0005-required-generated-human-verified.md)
* [ADR-0016: Distillation adds refutation](/base/decisions/standard/SDR-0010-refutation-as-a-distillation-kind.md)
* [ADR-0017: Agent skills per platform](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md)
* [Conflict log](/conflict-log.md)
* [Knowledge architect](/base/roles/knowledge-architect.md)

[^adr-0016]: ADR-0016, decision 3.
[^adr-0005]: ADR-0005: `verified` only by a person, as an explicit act.
[^adr-0017]: ADR-0017: the M365 agent's skills come from `tools/m365-agent.json`.
