---
type: Runbook
title: Build a change in layers
description: Procedure for taking a multi-stage change of the repo from decision to merge through delegated tickets, fresh-context review and verification on main.
tags: [runbook, process, agents]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Trigger

A change that touches several layers (standard, scripts, skills, `knowledge/`) or more files than one session can review with care. Small fixes, debugging with an unknown cause and unsettled designs do not use this runbook: they are done inline or clarified with the owner first. The decision is in [ADR-0009](/decisions/ADR-0009-build-in-layers-and-tickets.md).

# Steps

1. **Decide with the owner.** What is a decision (a new ADR with `okf-capture`, the vocabulary, a term glossary) is not a ticket: it is settled with the owner before building.
2. **Split into layers** in dependency order, and each layer into tickets of at most about 50 files with a closed file list. At most 3 tickets in parallel.
3. **Write each ticket** with:
   - behavior as an input → expected output table;
   - pattern to copy as `file:line`;
   - acceptance criteria, each with the test (or check) that fails if the change is reverted;
   - "builds on": what must already exist on main; if it does not exist, the builder stops;
   - exact verification commands (`make test`, `make lint`, the layer's grep).
4. **Open one record per ticket** in whichever tracker is used and store the ticket text in it.
5. **Run each ticket:**
   1. *Pre-flight*: an agent reads the ticket against the code and flags false premises, ambiguities and decisions that belong to the owner.
   2. *Builder*: works in a worktree, proves each criterion (revert → red → restore), pastes the output into the PR body and opens the PR as a draft.
   3. *Review*: one or two reviewers with fresh context, without the builder's report. Use two lenses (correctness, tests) if the standard, the linter or a skill is touched. Findings are classified as blocking, to fix or nit; only blocking findings force a round of fixes.
   4. *Fixes*: at most two rounds; if that is not enough, the ticket goes back to the owner.
6. **Verify and merge from the main session:** run `make test` and `make lint` on main with the branch merged, merge the PR and close the record citing the PR. Pending nits go to a single follow-up record.
7. **Push main before the next layer.** The agents' worktrees branch off `origin/main`, not the local main: a layer merged only locally is invisible to the next one.

# Warnings

- An agent's report is a claim: the state is read from the PR and from the output of the checks, not from the answer (which may arrive truncated).
- Launching an agent workflow requires a written message from the owner that names the tickets; an approval given through a question dialog is not enough.
- An agent only stops processes it started itself, never by process name.
- Resuming a workflow reruns the agents after the first change: to continue a half-finished run, pass its state (PR, branch, stage) as the starting point.

# Rollback

Each ticket is its own PR: revert the merge of the affected PR. If a layer already has dependent tickets merged, revert in reverse layer order.
