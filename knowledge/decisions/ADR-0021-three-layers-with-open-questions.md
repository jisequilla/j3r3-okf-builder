---
type: Architecture Decision
title: "ADR-0021: A bundle has three layers in profile knowledge/3.0; open questions are concepts in base/ and action items live in the team's tracker"
description: The bundle separates what was said (fragments/), what is known (base/, holding the typed directories) and what is derived for a reader (projections/), in profile knowledge/3.0; an open question is an Open Question concept in base/ with an owner, and an action item lives in the team's tracker, never copied into the base.
tags: [adr, standard, profile, layers]
status: draft
adr_id: ADR-0021
decision_status: accepted
supersedes: /decisions/ADR-0018-three-layers-fragments-base-projections.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T09:40:00Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
  - { id: tool, resource: /fragments/2026-11-02-migration-tool-okf-review.md, title: "Fragment: what a long-running OKF implementation teaches" }
  - { id: adr-0016, resource: /decisions/ADR-0016-refutation-as-a-distillation-kind.md }
---

# Context

[ADR-0018](/decisions/ADR-0018-three-layers-fragments-base-projections.md) gave a bundle three layers, `fragments/`, `base/` and `projections/`, moved the typed directories under `base/` and raised the profile to knowledge/3.0[^bundles]. Its decision 5 kept action items in fragments, out of the base.

A migration tool that has kept twelve OKF bundles for months shows what that costs. Meetings produce questions and actions with an owner, what they block, a review date and a default if unanswered. In a fragment nobody can track them: the record is immutable and holds no state. The tool keeps each such item in the one surface of the system that executes or answers it, and every other surface links to it; its design meetings put it as "memory holds only decisions and open questions; what is pending lives in the tracker"[^tool]. The owner chose to keep open questions in the bundle, as concepts with an owner, and to send action items to the team's tracker. The rest of ADR-0018 stands; it is restated here so this ADR is complete.

# Decision

1. **A bundle has three layers**, each in its own directory under `knowledge/`:

   | Layer | Directory | What it holds | Who writes it |
   |---|---|---|---|
   | Record | `fragments/` | Events as they happened: meetings, chats, transcripts, slides. The record is immutable after capture | `okf-fragment` |
   | Knowledge | `base/` | The current state of what is known, as OKF concepts in the typed directories, including open questions | `okf-capture`, `okf-distill`, `okf-review` |
   | Derivation | `projections/` | What is derived from the base for a reader; not OKF concepts ([ADR-0022](/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)) | projection tools |

2. **The typed directories move under `base/`**: `base/architecture/`, `base/decisions/`, `base/domain/`, `base/systems/`, `base/apis/`, `base/data/`, `base/metrics/`, `base/computations/`, `base/runbooks/`, `base/playbooks/`, `base/policies/`, `base/references/`, `base/questions/`, and any directory a bundle adds. Bundle paths follow (`/base/decisions/ADR-0001-....md`).
3. **The root keeps only what is about the bundle as a whole**: `index.md` (with `okf_version` and `okf_profile`), `log.md`, `project.md` and `conflict-log.md`, plus the three layer directories.
4. **Writing in `base/`**: concepts state the current state in the present tense, with their sources; dated history goes to `log.md` and to the fragments, not into the prose. A concept with several topics, or longer than about 300 lines, is split.
5. **What a fragment's content becomes**:

   | In the fragment | Goes to |
   |---|---|
   | A decision, a fact, a definition | A concept in `base/` (`okf-distill`) |
   | A question nobody has answered | An `Open Question` concept in `base/questions/` |
   | A proposal nobody has validated | An ADR with `decision_status: proposed`, or an open question |
   | An action item (someone must do something) | The team's tracker; the base never copies it, and a concept may link the tracker item |
   | Logistics, tone, commercial terms | Nothing: they stay in the fragment's record |

6. **An `Open Question`** carries `owner` (an actor, required), `question_status` (`open`, `answered` or `dropped`), `asked_in` (the fragment where it arose), and optionally `blocks` (the concepts it holds up), `review_on` (a date) and `answered_by` (the concept that answers it). An answered question is not deleted: it links its answer.
7. **The profile becomes `knowledge/3.0`.** `okf_lint` validates 2.0 and 3.0 bundles by the `okf_profile` the root declares, and `okf-init` writes 3.0. `okf-migrate` moves a 2.0 bundle to 3.0: it moves the typed directories under `base/`, rewrites the bundle-path links and `sources` that point into them, and logs a **Migration** entry. The OKF version (0.1 or 0.2) is independent of the profile and does not change.
8. **OKF tools read `fragments/` and `base/`, and skip `projections/`.**

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| ADR-0018: action items stay in fragments | One place for what was said | Nobody can track an item inside an immutable record | Open work needs a home with state |
| Action items as concepts in `base/` | Everything in one bundle | The base would duplicate the tracker, and the two drift | One surface per item; the tracker already holds state and owners |
| Open questions in the tracker too | One rule for open work | The question is knowledge: what the team does not know yet, which `okf-ask` must report | Questions are knowledge; actions are work |
| Keep the typed directories at the root | No migration | The boundary works by exclusion and is not visible | Decided in ADR-0018; unchanged |

# Consequences

- Positive: open questions are answerable and tracked by owner; action items have one home; the three layers stay visible in every bundle.
- Negative / accepted debt: a new type, `Open Question`, in the standard and in the templates; `okf-distill` routes action items outside the bundle and cannot verify they were filed; the rest of ADR-0018's debt (the migration of every 2.0 bundle) stands.
- Follow-up actions: those of ADR-0018; the `Open Question` type in the standard and a template; `okf-distill` routes each item by the table in decision 5; `okf-review` lists open questions by owner and age; `okf-ask` reports the open questions that touch an answer.

# Related

* [ADR-0018: A bundle has three layers](/decisions/ADR-0018-three-layers-fragments-base-projections.md)
* [ADR-0022: Knowledge projections, drift by nature](/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)
* [ADR-0023: One Domain Profile per bundle](/decisions/ADR-0023-domain-profile-per-bundle.md)

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
[^tool]: Fragment of 2026-11-02, the review of a long-running OKF implementation and its design meetings.
