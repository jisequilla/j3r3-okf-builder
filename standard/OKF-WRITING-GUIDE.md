# OKF writing guide

This guide says how to write a concept in an OKF bundle. An agent that writes a concept follows it. The person who verifies the concept reads it against this guide. It applies to every concept type and every bundle.

## 1. What a section holds

- Each section of a concept holds only what its note in the type's template says.
- How a concept was reached (the options weighed, the rounds, the dates of the discussion, a person's words) lives in the source fragment, which the concept links with a footnote.

**How to use a note.** A template gives each section one note: a line in double braces, `{{...}}`, directly under the section's heading. The note says what the section holds and how long it is.

1. Write the section from its note.
2. Replace the note with the section's text.
3. Keep and fill the scaffolding under the note: a table header, a list of lines such as `- Positive: ...`, an example link.
4. Delete the pointer line, the template's first line under the frontmatter, which names this guide.

A finished concept holds no note and no pointer line.

## 2. The eight style rules

Every concept follows these rules.

1. **Plain words.**
   - Before: "The skill leverages the index to facilitate the retrieval of concepts."
   - After: "The skill reads the index to find concepts."
2. **One idea per sentence.**
   - Before: "Lint checks the links and, when one is broken, reports a warning, which the person then fixes."
   - After: "Lint checks the links. It reports each broken link as a warning. The person fixes it."
3. **Active voice, with the actor named.**
   - Before: "The concept is verified before it is moved to stable."
   - After: "The owner verifies the concept and moves it to stable."
4. **A term is defined once and kept.**
   - Before: "A fragment records the meeting. Later, okf-distill reads the meeting note."
   - After: "A fragment records the meeting. Later, okf-distill reads the fragment."
5. **No history of the editing.**
   - Before: "This section now also covers rollbacks, added after the review."
   - After: "This section covers rollbacks."
6. **Written in the bundle's language. The rules apply in any language; the guide is in English.**
   - Before, in a Spanish bundle: "The team deploys on Fridays."
   - After: "El equipo despliega los viernes."
7. **A section states what is true now, not how it was reached: options weighed, rounds and dates of the discussion stay in the fragment.**
   - Before: "After two rounds on 3 March, the team chose Postgres over MySQL."
   - After: "The service stores its data in Postgres."
8. **A person's words are quoted in the fragment; the concept links it with a footnote.**
   - Before: 'Ana said: "we cannot afford a second database."'
   - After: "The team runs one database.[^meeting]"

## 3. A worked example: a decision's Context

**Before.** A decision's first Context spent three paragraphs on how the decision was reached, and only then gave its examples. It held sentences such as these:

> The first plan kept DEC-0002 and added the two sessions beside it. It let a change only under `knowledge/` be built inline, which contradicts DEC-0002 decisions 3 and 5.

These sentences tell the story of the discussion: a first plan, and why it failed. The person who verified the decision did not confirm it.

**After.** The confirmed Context holds two parts:

1. One paragraph of the forces that make the decision needed now: what the earlier rule gave, and why it no longer fits.
2. The same worked examples, each one a before and an after.

The first plan and the rounds that replaced it are in the source fragment. The Context links that fragment with a footnote.

## 4. Where the discussion goes

The discussion goes in the source fragment. A fragment keeps a meeting, a transcript or a chat as it happened, a person's words included.

The concept links the fragment in two places:

1. An entry in `sources`, such as `{ id: meeting, resource: /fragments/2026-03-03-database-choice.md }`.
2. A footnote on each claim the fragment supports, such as `The team runs one database.[^meeting]`, with the footnote's text at the end of the concept.

A reader who wants to know how the concept was reached follows the footnote.

## 5. Who checks

- The person who verifies a concept reads it against this guide.
- Nothing checks these rules mechanically: no lint rule and no field enforce them.
- A concept written before this guide is not rewritten. It follows the guide when it is next changed.

## 6. By concept type

Each entry gives the notes of a type's template, one per section.

### Decision and Architecture Decision

- **Context**: The forces that make a decision needed now, in one paragraph. Then a worked example, before and after. Not how the decision was reached: that is in the source fragment.
- **Decision**: What is decided, as numbered points, each one sentence a reader can act on.
- **Alternatives considered**: One row per option really weighed, with the reason it lost in a phrase.
- **Consequences**: What changes for the reader. One line each: positive, accepted debt, follow-up.
- **Related**: Links only, one per line.
