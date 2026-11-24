---
type: Standard Decision
title: "SDR-0028: Each section of a concept holds only what its template's note says, how the concept was reached stays in its source fragment, and every concept follows eight style rules"
description: Each section of a concept holds only what its note in the type's template says; the options weighed, the rounds, the dates of the discussion and a person's words live in the source fragment, which the concept links with a footnote; eight style rules apply to every concept in the bundle's language; a decision's five sections get notes on what belongs and how long, every other template gets its own notes; the owner checks a concept against them when verifying it, with no lint rule and no new field; existing concepts follow them when next changed.
tags: [decision, standard, writing, templates]
status: stable
decision_id: SDR-0028
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-24T06:43:13Z }
verified: [{ by: human:jisequilla, at: 2026-11-24T06:45:48Z }]
sources:
  - { id: fragment, resource: /fragments/2026-11-23-how-a-concept-is-written.md, title: "2026-11-23 · How a concept is written, the owner's answers on what each section holds and the language of a concept" }
  - { id: dec-0006-verification, resource: /fragments/2026-11-17-verification-dec-0006.md, title: "2026-11-17 · Verification of DEC-0006 on the Knowledge Viewer, after a first version was not confirmed" }
  - { id: dec-0006, resource: /base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md }
  - { id: sdr-0022, resource: /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md }
---

# Context

Agents write most concepts in an OKF bundle, and a person verifies each one before it is stable[^sdr-0022]. Each template gives one hint per section, such as "Forces at play", but nothing says what a section must leave out, how long it is, or how its sentences are written. So an agent fills a section with whatever it knows, including how the concept was reached, and the person who verifies it has no stated rule to check it against. A source fragment already holds the record of the discussion[^fragment], so a concept that repeats it holds the same text twice, and the person has to read past it to find what is true now.

**Worked example.** DEC-0006's first Context spent three paragraphs on how the decision was reached before its examples, for instance: "The first plan kept DEC-0002 and added the two sessions beside it. It let a change only under `knowledge/` be built inline, which contradicts DEC-0002 decisions 3 and 5."[^fragment] The owner did not confirm it[^dec-0006-verification]. The confirmed version, [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md), gives one paragraph of the forces and then the same examples.

# Decision

1. Each section of a concept holds only what its note in the type's template says.
2. How a concept was reached (the options weighed, the rounds, the dates of the discussion, a person's words) lives in the source fragment, which the concept links with a footnote.
3. Every concept follows eight style rules:
   1. Plain words.
   2. One idea per sentence.
   3. Active voice, with the actor named.
   4. A term is defined once and kept.
   5. No history of the editing.
   6. Written in the bundle's language. The rules apply in any language; the guide is in English.
   7. A section states what is true now, not how it was reached: options weighed, rounds and dates of the discussion stay in the fragment.
   8. A person's words are quoted in the fragment; the concept links it with a footnote.
4. The decision and adr templates carry these notes for a decision's five sections:
   - Context: the forces that make a decision needed now, in one paragraph. Then a worked example, before and after. Not how the decision was reached: that is in the source fragment.
   - Decision: what is decided, as numbered points, each one sentence a reader can act on.
   - Alternatives considered: one row per option really weighed, with the reason it lost in a phrase.
   - Consequences: what changes for the reader. One line each: positive, accepted debt, follow-up.
   - Related: links only, one per line.
5. Every other concept template gets a note per section in the same manner.
6. No lint rule and no new field enforce these rules: the owner checks a concept against the guide when verifying it.
7. Existing concepts are not rewritten: a concept follows these rules when it is next changed.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| A DEC, or both a DEC and an SDR | Sits beside this repository's process decisions | How a concept is written applies to every bundle, not only to this repository | It is a decision about the standard |
| Style rules only, the language unsaid | One rule less | A bundle written in Spanish gets no rule on its language | The bundle's language is part of the rule |
| The language declared in the Domain Profile | Explicit per bundle | A new field to define and check | The bundle's language needs no field |
| Every section note written in this decision | One place for all the text | About 70 notes for 15 templates in one decision | The notes are settled on a page of their own |
| Section notes left to whoever writes the templates | No extra review | The owner never reads them before they apply | The owner reads them before they merge |
| The six style rules only | Shorter list | Misses the two rules DEC-0006's first version broke | Rules 7 and 8 name what that version did wrong |
| The eight rules with numeric limits | Measurable | A limit fits a section, not a rule | Each section's note sets its length |
| Section notes that say only what belongs | Shorter notes | Says nothing on length, so a Context can grow again | A note says what belongs and how long |

# Consequences

- Positive: a person verifying a concept checks it against stated rules, and a decision's Context reads as the forces and an example, with the discussion one footnote away.
- Accepted debt: nothing checks the rules mechanically, so a concept that breaks them passes lint and depends on the person who verifies it; existing concepts stay as written until they change.
- Follow-up: layer 1 of tracker item okf-eb5 writes the guide in `okf-standard/references/` with this example, the note per section in every concept template, and the pointers from `okf-capture`, `okf-distill` and `okf-review`.

# Related

* [DEC-0006: Two sessions maintain this repository, a router that plans and reviews and a worker that builds, and each of three kinds of change has its own review](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md)
* [SDR-0022: An agent writes a person's verification only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and version](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)
* [SDR-0007: Knowledge fragments are captured as they happened and distilled into the bundle](/base/decisions/standard/SDR-0007-knowledge-fragments-and-distillation.md)

[^fragment]: The owner's words and answers, and DEC-0006's first Context quoted in full, in the source fragment.
[^dec-0006-verification]: The owner's comment on the first version and the confirmation of the second, in the verification fragment of DEC-0006.
[^sdr-0022]: SDR-0022: a person's verification is recorded from their answer to a structured question or on a review page.
