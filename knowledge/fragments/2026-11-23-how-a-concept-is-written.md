---
type: Knowledge Fragment
title: 2026-11-23 · How a concept is written, the owner's answers on what each section holds and the language of a concept
description: The owner's words and answers of 2026-11-17 and 2026-11-23 on how a concept is written, what each section holds, where the discussion that reached it is kept, the eight style rules and the notes for a decision's five sections, with the Context of DEC-0006's first, not confirmed version quoted in full, distilled into SDR-0028.
tags: [fragment, standard, writing]
status: draft
occurred_at: 2026-11-23
origin: Claude Code session okf-router-session in this repository, on 2026-11-17 and 2026-11-23; the tracker records okf-eb5 and okf-eb5.1
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "8fa73bade9fe88f679d4f55f88ec82684673f1f7" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-24T06:43:13Z }
sources:
  - { id: dec-0002, resource: /base/decisions/DEC-0002-build-in-layers-and-tickets.md, title: "Cited by the quoted Context of DEC-0006's first version" }
  - { id: fragment, resource: /fragments/2026-11-17-maintenance-harness.md, title: "Cited by the quoted Context of DEC-0006's first version" }
  - { id: pr-133, resource: "https://github.com/jisequilla/j3r3-okf-builder/pull/133#issuecomment-6901168187", title: "Cited by the quoted Context of DEC-0006's first version" }
---

# Record

## What the owner asked for, 2026-11-17

On pull request #136, verifying DEC-0006 on the Knowledge Viewer (round okf-m41.1), the owner did not confirm its first version, with the comment "i think greate part of the context should go into a fragment, we should keep decissions lean and not so much about the discussion of how we got there, that is what the fragment is for". The stored answer and the second, confirmed version are kept in [2026-11-17 · Verification of DEC-0006 on the Knowledge Viewer, after a first version was not confirmed](/fragments/2026-11-17-verification-dec-0006.md).

Two answers followed the same day, recorded in the tracker record okf-eb5; the text of the questions was not kept there.

- Asked by structured question when the rule should be written, the owner chose "Rule, after harness": a rule on how a concept is written, built after the maintenance harness (tracker epic okf-m41).
- The owner then asked for a guideline on how to write decisions: "maybe the teamplate should come with an explanation on the language and how to write it". Asked about its scope, the owner chose "Every concept type".

## The owner's answers, 2026-11-23

Five structured questions in the router session.

Q1. "okf-eb5, layer 0: which kind of decision records how a concept is written? In this repo SDR is a decision about the standard itself, DEC is about how this repo works, ADR is about how the plugin is built." Options: "SDR-0028 (Recommended)", "DEC-0007", "Both". Answer: "SDR-0028 (Recommended)".

Q2. "okf-eb5: you asked for 'an explanation on the language and how to write it'. The ticket covers the style (plain words, one idea per sentence, active voice, the actor named, terms defined once, no editing history). Should the decision also say which human language a concept is written in? The standard says nothing on it today, and the Santalucía bundles are in Spanish." Options: "The bundle's language (Recommended)", "Style only", "Declared in the Domain Profile". Answer: "The bundle's language (Recommended)".

Q3. "okf-eb5: the 15 concept templates have about 70 sections between them, and each gets a note saying what belongs there and how long it is. Where is the text of those notes settled with you?" Options: "Principle now, notes on a page (Recommended)", "All notes in the decision", "Notes left to the builder". Answer: "Principle now, notes on a page (Recommended)".

Q4. "SDR-0028: which style rules does the decision record? The ticket lists six. Reading DEC-0006's two versions, I'd add two that the not-confirmed version broke." Options: "The six plus two (Recommended)", "The six only", "Six plus two, with limits". Answer: "The six plus two (Recommended)", with these eight rules:

1. Plain words.
2. One idea per sentence.
3. Active voice, with the actor named.
4. A term is defined once and kept.
5. No history of the editing.
6. Written in the bundle's language. The rules apply in any language; the guide is in English.
7. A section states what is true now, not how it was reached: options weighed, rounds and dates of the discussion stay in the fragment.
8. A person's words are quoted in the fragment; the concept links it with a footnote.

Q5. "SDR-0028's worked example: the notes for a decision's five sections, as they would appear in the decision and adr templates. Which set?" Options: "What belongs, and how long (Recommended)", "What belongs only". Answer: "What belongs, and how long (Recommended)", with these five notes:

- Context: the forces that make a decision needed now, in one paragraph. Then a worked example, before and after. Not how the decision was reached: that is in the source fragment.
- Decision: what is decided, as numbered points, each one sentence a reader can act on.
- Alternatives considered: one row per option really weighed, with the reason it lost in a phrase.
- Consequences: what changes for the reader. One line each: positive, accepted debt, follow-up.
- Related: links only, one per line.

## DEC-0006's first Context, not confirmed

The Context of DEC-0006 as the owner read it and did not confirm, quoted in full from commit `29fb120fa46b4739e45d4835ae9d549e15560b06` (`git show 29fb120:knowledge/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md`). No branch or tag contains that commit, so this quote is the durable copy of that version. The confirmed version is [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md), at `knowledge/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md`.

~~~~markdown
# Context

[DEC-0002](/base/decisions/DEC-0002-build-in-layers-and-tickets.md) made one session judge and never implement: every ticket went through pre-flight, a builder in a worktree, fresh-context reviewers and a rerun of the tests on the merged main, and every prose ticket carried a mechanical check and a meaning-drift pass[^dec-0002].

In November 2026 the work ran in two Claude Code sessions instead: one planned with the owner and wrote the tickets, the other built them. Two things showed in that run. A code change built inline with no reviewer passed its tests, lint and CI, and a second session that ran it on a bundle outside the repository found a defect before the merge; the owner asked for that review to become permanent, with a recipe and a prompt file to start each session[^fragment]. And a one-row reword of a concept went through a review, the owner's verification and a second review, which the owner called too much ceremony for a small change: "we should be able to focus on bringin value with order"[^fragment].

The first plan kept DEC-0002 and added the two sessions beside it. It let a change only under `knowledge/` be built inline, which contradicts DEC-0002 decisions 3 and 5. The owner, human:jisequilla, then chose in structured questions on 2026-11-17 to replace DEC-0002 with one rule that sorts changes into three kinds[^fragment].

**Worked examples.**

- A code change, before: okf-1lj.2 was built inline with no reviewer (pull request #133, commit `327ab0b`). Tests, lint and CI passed. The router ran the script on a probe bundle and found a defect in the default round, fixed in `6453caa`[^pr-133], but never opened the page it built, and two page defects reached main: the page fails to load for a bundle outside git, and its Conflict Log section is always empty (tracker item okf-1lj.8).
- A code change, after: the same change runs through the workflow, and the router opens the built page in a browser on a bundle outside git: the load failure is seen before the merge.
- A small knowledge change, before: a one-row reword of `knowledge-viewer.md` in pull request #135 got a router verdict, the owner's re-verification, and a second router verdict on the new head.
- A small knowledge change, after: the worker rewords the row, the owner verifies it in the worker session, CI's lint passes, the owner merges. No router review.
~~~~

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| What the owner asked for, 2026-11-17 | addition | applied | [SDR-0028](/base/decisions/standard/SDR-0028-how-a-concept-is-written.md) |
| The owner's answers, 2026-11-23 | addition | applied | [SDR-0028](/base/decisions/standard/SDR-0028-how-a-concept-is-written.md) |
| DEC-0006's first Context, not confirmed | — | worked example | [SDR-0028](/base/decisions/standard/SDR-0028-how-a-concept-is-written.md) |
