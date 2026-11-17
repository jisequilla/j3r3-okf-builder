---
type: Decision
title: "DEC-0006: Two sessions maintain this repository, a router that plans and reviews and a worker that builds, and each of three kinds of change has its own review"
description: A router session plans with the owner, writes the tickets and reviews each code change before its merge; a worker session builds; a small knowledge change is built inline and verified by the owner, a code change under plugin/ or build/ goes through the okf-layer-ticket workflow and then the router's review, which runs it and opens what it builds, and a decision or a change to the standard is settled with the owner first; CI on main is the check after a merge; supersedes DEC-0002.
tags: [adr, process, agents, review]
status: draft
decision_id: DEC-0006
decision_status: accepted
supersedes: /base/decisions/DEC-0002-build-in-layers-and-tickets.md
superseded_by:
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-17T21:22:01Z }
sources:
  - { id: fragment, resource: /fragments/2026-11-17-maintenance-harness.md, title: "Fragment: the maintenance harness" }
  - { id: dec-0002, resource: /base/decisions/DEC-0002-build-in-layers-and-tickets.md }
  - { id: doctrine, resource: /base/doctrine/building-with-agents.md }
  - { id: pr-133, resource: "https://github.com/jisequilla/j3r3-okf-builder/pull/133#issuecomment-6901168187", title: "The router's verdict on pull request #133" }
---

# Context

[DEC-0002](/base/decisions/DEC-0002-build-in-layers-and-tickets.md) made one session judge and never implement: every ticket went through pre-flight, a builder in a worktree, fresh-context reviewers and a rerun of the tests on the merged main, and every prose ticket carried a mechanical check and a meaning-drift pass[^dec-0002].

In November 2026 the work ran in two Claude Code sessions instead: one planned with the owner and wrote the tickets, the other built them. Two things showed in that run. A code change built inline with no reviewer passed its tests, lint and CI, and a second session that ran it on a bundle outside the repository found a defect before the merge; the owner asked for that review to become permanent, with a recipe and a prompt file to start each session[^fragment]. And a one-row reword of a concept went through a review, the owner's verification and a second review, which the owner called too much ceremony for a small change: "we should be able to focus on bringin value with order"[^fragment].

The first plan kept DEC-0002 and added the two sessions beside it. It let a change only under `knowledge/` be built inline, which contradicts DEC-0002 decisions 3 and 5. The owner, human:jisequilla, then chose in structured questions on 2026-11-17 to replace DEC-0002 with one rule that sorts changes into three kinds[^fragment].

**Worked examples.**

- A code change, before: okf-1lj.2 was built inline with no reviewer (pull request #133, commit `327ab0b`). Tests, lint and CI passed. The router ran the script on a probe bundle and found a defect in the default round, fixed in `6453caa`[^pr-133], but never opened the page it built, and two page defects reached main: the page fails to load for a bundle outside git, and its Conflict Log section is always empty (tracker item okf-1lj.8).
- A code change, after: the same change runs through the workflow, and the router opens the built page in a browser on a bundle outside git: the load failure is seen before the merge.
- A small knowledge change, before: a one-row reword of `knowledge-viewer.md` in pull request #135 got a router verdict, the owner's re-verification, and a second router verdict on the new head.
- A small knowledge change, after: the worker rewords the row, the owner verifies it in the worker session, CI's lint passes, the owner merges. No router review.

# Decision

What DEC-0002 decided and still holds: a change is built in **layers in dependency order**, what the owner decides first, merged and on `origin/main` before the layers that depend on it; **one ticket per unit of work**, precise by example (an input → expected output table, a closed list of files, the pattern to copy as `file:line`, exact verification commands); and each ticket has **its record in the tracker**, closed only after the merge and citing the pull request, with the repository depending on no tracker. The rest is replaced by the following.

1. **Two named sessions maintain this repository**: `okf-router-session` and `okf-worker-session`, each started by its recipe (`just router`, `just worker`) with a short prompt file kept in the repository.
2. **The router plans and does not build.** It reads the board and the repository, settles decisions with the owner by structured question, writes each ticket into the tracker, and releases a ticket to the worker only on the owner's word. It edits nothing in the repository and claims no ticket.
3. **Three kinds of change, each with its own review:**
   - **a. A small knowledge change**, only under `knowledge/` (a row reworded, a link fixed, a script list updated): the worker builds it inline, the owner verifies the concepts it changes in the worker session, and CI's lint is the check. No router review. Several such changes may share one pull request.
   - **b. A code change**, anything under `plugin/` or `build/`: through the `okf-layer-ticket` workflow, a builder in a worktree and fresh-context reviewers who challenge the ticket as well as the diff; then the router's review (decision 4).
   - **c. A decision, or a change to the standard**: settled with the owner by structured question first, and verified by the owner; the code it needs follows as its own tickets of kind b.
4. **The router reviews a code change before its merge, on the pushed head commit.** It runs the change on a bundle outside the repository, and when the change builds something a person uses (a page, an Obsidian vault) it also opens that output in the tool that reads it ([doctrine](/base/doctrine/building-with-agents.md) principle 12). Its verdict is a comment on the pull request naming the commit, what it ran, what it opened and what it did not. A later push needs a new verdict.
5. **After the merge, CI's run on main is the check of the merged main**: `.github/workflows/ci.yml` runs on every push to `main`. DEC-0002's rerun of the tests by the main session is dropped.
6. **The merge, and every commit, branch and pull request, stay the owner's word**, given in the worker session (doctrine principle 10).
7. **The rules live in `knowledge/`**: this decision and the runbook [Build a change in layers](/base/runbooks/build-in-layers.md). The two prompt files say which session this is and point at them; they restate no rule.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep DEC-0002 and add the two sessions beside it | No decision superseded | A knowledge change built inline contradicts its decisions 3 and 5, so two decisions in force would disagree | The owner chose one rule that replaces it |
| Two kinds only, code and everything else | Simpler | A decision or a change to the standard would be built before the owner settled it | A decision is settled first, as DEC-0002's layers already asked |
| Every change through the workflow | One path; nothing built without a reviewer | A one-row reword costs a builder, two reviewers, a classifier and a router review | The owner verifies a small knowledge change, and that is its review |
| The worker chooses how to build, with a fixed review | Flexible | Pull request #133 was built inline with no reviewer under that freedom | A code change always goes through the workflow |
| The worker reruns the tests on main after each merge | A second check of the merged main | A step for a result CI already gives on every push to main | CI on main is enough |
| The router only runs the change on a bundle | A few minutes less per review | Pull request #133's page defects were visible only in the browser | It opens what the change builds when a person uses it |
| The verdict as a message between the sessions, or a tracker comment | Nothing written to GitHub by the router | Not visible at the merge, lost with the session | A comment on the pull request, naming the commit |
| The recipes and prompts kept local | Nothing new in the repository | Not versioned or reviewed, and a clone has no way to start the sessions | Checked into the repository |

# Consequences

- Positive: a small fix to the knowledge base costs one verification by the owner and one merge; a code change is always built with reviewers and then run, and opened, by a session that did not build it; the review is on the pull request where the merge happens; nobody reruns what CI already runs.
- Negative / accepted debt: a small knowledge change has no reviewer but the owner, and the mechanical check and meaning-drift pass DEC-0002 asked of every prose ticket are no longer required; which changes are "small" is a judgment the router and the owner make per ticket; the router writes to GitHub; the two sessions depend on Claude Code sessions messaging each other on one machine.
- Follow-up actions (tracker epic okf-m41): the recipes `just router` and `just worker`, the two prompt files and the reviewers' instruction to challenge the ticket (layer 1); the runbook [Build a change in layers](/base/runbooks/build-in-layers.md) and the [doctrine](/base/doctrine/building-with-agents.md), which still describe DEC-0002's single main session, updated to this decision (layer 2), with every concept that links DEC-0002 as the rule in force.

# Related

* [DEC-0002: Build multi-stage changes in layers and delegated tickets](/base/decisions/DEC-0002-build-in-layers-and-tickets.md), superseded by this decision
* [Build a change in layers](/base/runbooks/build-in-layers.md)
* [Building with agents](/base/doctrine/building-with-agents.md)
* [DEC-0003: Where things go](/base/decisions/DEC-0003-where-things-go.md)

[^dec-0002]: DEC-0002, decisions 3, 4 and 5.
[^fragment]: 2026-11-17 · The maintenance harness, Record.
[^pr-133]: The router's verdict on pull request #133, comment 6901168187.
