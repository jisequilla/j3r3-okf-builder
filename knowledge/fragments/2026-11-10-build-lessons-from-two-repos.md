---
type: Knowledge Fragment
title: 2026-11-10 · How two other repos build with agents, and what this repo takes from them
description: The answers of two agent sessions in other repositories of the owner, one that builds inline and one that interviews and delegates tickets to workflows, to how they implement; the agent's comparison with this repo's workflow; and the owner's choices on how the next build work runs and what changes in the workflow, the tickets and the doctrine.
tags: [fragment, decision, agents, workflow, process]
status: draft
occurred_at: 2026-11-10T23:43:28Z
origin: Claude Code session in this repository, with messages to and from two sessions in other repositories
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "faad421d18e4653af025351f2fccce1b1fafa613" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-10T23:43:28Z }
---

# Record

## The question

The owner asked, in their words:

> so what about implementation, should we use something like dynamic workflows like the sdam project, check with it's claude code open session how it is so we can review if it is a good idea to use it or even the grill room session, both are open and we can have feedback about it, what do you think?

The agent noted that this repo already runs implementation through an agent workflow, `.claude/workflows/okf-layer-ticket.js` ([Build a change in layers](/base/runbooks/build-in-layers.md), [Building with agents](/base/doctrine/building-with-agents.md)), and that this session had built okf-3vg.1 and okf-3vg.2 itself, against principle 1; one fresh-context review still found a crash and an instance linted twice. It asked both sessions, read only, how they build.

## The inline repo

Its session answered, from its repository and its 11 session transcripts, that it has never run implementation through a workflow: the main session claims a ticket, writes the code inline on a branch, opens a pull request and merges it (16 pull requests, 26 of 33 tickets), and asks the owner in the moment with a structured question when a decision comes up. Its rule: inline when verification needs the owner's eyes or hardware, a workflow when the checks are machine-decidable, which this repo's lint is. Its incident: another session kept writing into the working tree after handing off, so a pull request merged code nobody had reviewed; the lesson is to verify the exact commit that was reviewed and merge only that one. Its advice for this repo: one ticket per run, so one ticket's defect does not contaminate the others' reviews, and a merge that checks the reviewed commit is the merged one. Worth copying: a pre-commit hook that refuses a commit when a generated projection is stale, a deterministic gate that fails on a known case.

## The interviewing repo

Its session answered that an interview settles decisions but did not make acceptance testable; a ticket template and a per-ticket pre-flight did. Its template asks for behaviour as an input → expected output table, each acceptance line naming the test that fails with the change reverted, each "never happens" line naming a planted bug that must make it fail, whole-value compares for exact outputs, and open questions empty before launch. A read-only pre-flight per ticket lists wrong premises, ambiguities, contradictions, boundary gaps and decisions only the owner can make, sent to the owner before launch; without it owner decisions came a review round late. Builders report what the prompt left unclear: 24 of 33 prompts had such a gap. Two ways its interview went wrong: the recommended option carried a median of 146 characters of reasoning and each alternative 29, so the owner kept accepting the recommendation; and an interview without the code designed what already existed. Every defect that passed its tests sat between tickets, not inside one. Its advice: interview before the decision record, with the code; per ticket, a pre-flight rather than another interview.

## The comparison

The agent compared both answers with `okf-layer-ticket.js`: its pre-flight already lists owner decisions and stops the run, and its builder proves each criterion by revert → red → restore; it does not record which commit the reviewers read nor check it at merge, its builder's report has no list of what the ticket left unclear, its tickets carry no planted-bug or whole-value rule, nothing checks across the tickets of a layer, and the agent's own questions to the owner had given the recommended option most of the reasoning.

## The owner's choices

To structured questions:

- How the remaining okf-3vg work runs: "Workflow for .5/.6, inline .4": okf-3vg.5 and okf-3vg.6 through `okf-layer-ticket`, one ticket per run; okf-3vg.4 built inline with one fresh-context review.
- Which changes land before the next run (several chosen): "Pin reviewed SHA", "Builder reports gaps", "Ticket rules" (planted bugs, whole-value compares, open questions empty before launch) and "Equal-depth questions" (every option of an owner question gets the same depth of reasoning, as a principle of the doctrine).
- How the decisions behind okf-jel and okf-waq are gathered: "Grill with code first": an interview with access to the code, walking every branch until nothing is assumed, before their decision records.

# Distillation

The change set was shown on a private review page, each item with its edit, its reasons, its costs and its alternatives at the same depth; on 2026-11-11 the owner chose **Apply** for all eight items, with no notes (okf-6q0). For the two items raised by the other sessions, X1 and X2, the first option, adding each now, was read as the one applied.

What went where: principle 1 of [Building with agents](/base/doctrine/building-with-agents.md) gains this session's evidence (D1) and the doctrine gains principles 13 (D13) and 14 (D14); [Build a change in layers](/base/runbooks/build-in-layers.md) gains the ticket rules in step 3 (W1), the builder's "Left unclear" section in step 5.2 (W3), the reviewed head commit in step 5.3 and the pinned merge in step 6 (W2), the layer review in step 7 (X1) and the pre-commit hook in Warnings (X2). Outside `knowledge/`, `.claude/workflows/okf-layer-ticket.js` returns `unclear`, `reviewed_sha` and `sha_mismatch` (W2, W3), and `.githooks/pre-commit` with `just hooks` carries out X2.

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The question | — | context | no concept (what the owner asked and why the two sessions were consulted) |
| The inline repo | Addition | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| The inline repo | Update | applied | [Build a change in layers](/base/runbooks/build-in-layers.md) |
| The interviewing repo | Addition | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| The interviewing repo | Update | applied | [Build a change in layers](/base/runbooks/build-in-layers.md) |
| The comparison | Confirmation | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| The owner's choices | — | context | no concept (how okf-3vg.4 to okf-3vg.6 run and how okf-jel and okf-waq are grilled are kept in their beads) |
