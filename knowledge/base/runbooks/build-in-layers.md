---
type: Runbook
title: Build a change in layers
description: Procedure for taking a multi-stage change of the repo from decision to merge through delegated tickets, fresh-context review and verification on main.
tags: [runbook, process, agents]
status: stable
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-12T21:34:01Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:56:18Z }, { by: human:jisequilla, at: 2026-11-11T18:24:16Z }, { by: human:jisequilla, at: 2026-11-12T21:41:17Z }]
---

# Trigger

A change that touches several layers (standard, scripts, skills, `knowledge/`) or more files than one session can review with care. Small fixes, debugging with an unknown cause and unsettled designs do not use this runbook: they are done inline or clarified with the owner first. The decision is in [ADR-0009](/base/decisions/ADR-0009-build-in-layers-and-tickets.md).

# Steps

1. **Decide with the owner.** What is a decision (a new ADR with `okf-capture`, the vocabulary, a term glossary) is not a ticket: it is settled with the owner before building.
2. **Split into layers** in dependency order, and each layer into tickets of at most about 50 files with a closed file list. At most 3 tickets in parallel.
3. **Write each ticket** with:
   - behavior as an input → expected output table;
   - pattern to copy as `file:line`;
   - acceptance criteria, each with the test (or check) that fails if the change is reverted;
   - each "never happens" criterion names a planted bug, and its check must fail with that bug applied;
   - exact outputs (a code list, a message, a JSON shape) are compared as whole values, not by "contains";
   - an "Open questions" section, empty before launch: a question still in it goes to the owner or into the ticket's text;
   - "builds on": what must already exist on main; if it does not exist, the builder stops;
   - exact verification commands (`just test`, `just lint`, the layer's grep);
   - the human-verified concepts it must edit, by path: no agent may verify them again (rule 6 of the [agents policy](/base/policies/agents-in-this-repo.md)), so `just lint` at `--strict` stays red with `VERIFIED_STALE` on each of them, the bar exempts that warning and nothing else, and the owner verifies them again after the merge, once for all the tickets of the layer that edit them;
   - the blocking bar: which failures block the merge (for example, a criterion not met or a regression in an existing check) and which do not (edge cases outside the ticket's input table). Without a bar written in advance, each review round finds new exotic cases and the fixes do not converge.
4. **Open one record per ticket** in whichever tracker is used and store the ticket text in it.
5. **Run each ticket** with the agent workflow `okf-layer-ticket` (`.claude/workflows/okf-layer-ticket.js`), which carries out the [Building with agents](/base/doctrine/building-with-agents.md) doctrine: one ticket per run, launched only after the owner's written message naming that ticket (see Warnings), with the args `{ ticket, ticketPath, commonPath, bead, continueBranch? }` (the ticket's id, its file, the context file common to every ticket, its tracker record and, to resume an interrupted builder, the branch holding its WIP commit). The workflow runs these stages:
   1. *Pre-flight*: an agent reads the ticket against the code and flags false premises, ambiguities and decisions that belong to the owner.
   2. *Builder*: works in a worktree, proves each criterion (revert → red → restore), pastes the output into the PR body and opens the PR as a draft. It lists what the ticket left unclear and the reading it took, in a "Left unclear" section of the PR body.
   3. *Review*: two reviewers with fresh context, without the builder's report, one per lens: correctness (the diff does what the ticket says, without contradicting the ADRs the ticket or the common context names, and without regressions) and tests (each criterion's check would fail if the change were reverted). Each labels its findings blocking, to fix or nit. Each reviewer records the PR head commit it read; the workflow returns it as `reviewed_sha` when every reviewer of the last round read the same one, and `sha_mismatch` when they did not.
   4. *Classification*: one more agent with fresh context reads the ticket's bar and every finding of the round, not the PR, and rules which ones the bar makes blocking, whatever their label ([Building with agents](/base/doctrine/building-with-agents.md), principle 7). Only its blocking findings force a round of fixes. If it gives no ruling for every finding, the workflow falls back on the reviewers' labels and returns `classifier_failed`, and the main session classifies the findings itself.
   5. *Fixes*: at most two rounds; if that is not enough, the ticket goes back to the owner.

   Two more entries reuse the same stages. `fix: { pr, branch, findings }` starts at the fixes, with findings the main session or the owner classified as blocking, then reviews and classifies again. `rebase: { pr, reviewed_sha, files }` runs only one reviewer with fresh context on a PR rebased after its review: with `git range-diff` it checks that the rebase changed only the conflicting files, and only to reconcile them with main, and it returns the new head as `reviewed_sha` if so, or `null` with its findings.
6. **Verify and merge from the main session:** run `just test` and `just lint` on main with the branch merged; when the change produces a file another tool reads, open a clean checkout in that tool and check what the ticket names ([Building with agents](/base/doctrine/building-with-agents.md), principle 12); merge the PR with `gh pr merge --squash --match-head-commit <reviewed_sha>`, which refuses if the head moved after the last review (then review again), and close the record citing the PR ([Building with agents](/base/doctrine/building-with-agents.md), principle 14). When another PR of the layer merged first and this one has to be rebased (they edit the same text files, such as `log.md`), run the workflow with `rebase`, and merge with the `reviewed_sha` it returns. When the layer's tickets named human-verified concepts, the owner verifies them again once they are on main, and main stays red at `--strict` only until then. Pending nits go to a single follow-up record.
7. **Push main before the next layer.** The agents' worktrees branch off `origin/main`, not the local main: a layer merged only locally is invisible to the next one. Before the next layer starts, one fresh-context reviewer reads the layer's merged diff as a whole (`git diff <layer start>..main`) for contracts split across tickets, names that collide and a ticket that assumed another's behaviour; a finding becomes a record of its own.

# Warnings

- An agent's report is a claim: the state is read from the PR and from the output of the checks, not from the answer (which may arrive truncated).
- Launching an agent workflow requires a written message from the owner that names the tickets; an approval given through a question dialog is not enough.
- An agent only stops processes it started itself, never by process name.
- `just hooks` installs the repository's pre-commit hook (`.githooks/pre-commit`) in a clone; it refuses a commit whose staged root copies or Obsidian setup are stale, and every worktree of that clone shares it.
- `just test` writes its scratch files to a directory of its own per run, but the exporters write `dist/` in the checkout, so two runs in one checkout collide. With tickets in parallel, only the builder runs `just test`; reviewers read the output pasted in the PR, and the main session runs it only after the agents finish.
- Resuming a workflow reruns the agents after the first change: to continue a half-finished run, pass its state (PR, branch, stage) as the starting point.

# Rollback

Each ticket is its own PR: revert the merge of the affected PR. If a layer already has dependent tickets merged, revert in reverse layer order.

# Related

* [Building with agents](/base/doctrine/building-with-agents.md)
* [ADR-0009: Build multi-stage changes in layers and delegated tickets](/base/decisions/ADR-0009-build-in-layers-and-tickets.md)
