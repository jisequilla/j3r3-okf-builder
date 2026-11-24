---
type: Runbook
title: Build a change in layers
description: Procedure by which the router and worker sessions take a change of the repo from decision to merge, by its kind, through tickets, the okf-layer-ticket workflow, the router's review of the pushed head and the merge on the owner's word.
tags: [runbook, process, agents]
status: stable
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-24T06:25:14Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:56:18Z }, { by: human:jisequilla, at: 2026-11-11T18:24:16Z }, { by: human:jisequilla, at: 2026-11-12T21:41:17Z }, { by: human:jisequilla, at: 2026-11-14T17:38:44Z }, { by: human:jisequilla, at: 2026-11-20T16:31:41Z }, { by: human:jisequilla, at: 2026-11-20T16:40:06Z }, { by: human:jisequilla, at: 2026-11-24T06:27:43Z }]
---

# Trigger

Any change to the repo. Two sessions maintain it: `okf-router-session`, the router, which plans with the owner, writes the tickets and reviews each code change before its merge, and `okf-worker-session`, the worker, which builds. The decision is [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md); this runbook is where its rules are carried out.

Start both sessions from the repository root with `just sessions`: it starts each with `hc run` in a terminal named after it that outlives the caller's, does not start one already live under its name, and, when `herdr-app` is on `PATH` and Herdr.app is open, shows both in its space `okf-builder`, in the tabs `router` and `worker`; its last line names only the sessions it placed there. Otherwise, reach them with `hc attach okf-router-session` and `hc attach okf-worker-session`. Without hc, run `just router` and `just worker` in a terminal each. Each recipe starts Claude Code under the session's name with its prompt file from `build/sessions/` appended to the system prompt, and its model and effort; the router's also passes `build/sessions/router.settings.json`, which denies file edits inside the repository. Arguments pass through, and a `--model` or `--effort` among them replaces the recipe's (`just worker --resume`).

# Steps

1. **Router: decide with the owner.** A decision or a change to the standard (DEC-0006, kind c) is not built first: it is settled with the owner by structured question (a new decision with `okf-capture`, the vocabulary, a term glossary) and verified by the owner, and the code it needs follows as its own tickets.
2. **Router: split into layers** in dependency order, and each layer into tickets of at most about 50 files with a closed file list. At most 3 tickets in parallel.
3. **Router: write each ticket** with:
   - its kind: a (only under `knowledge/`), b (anything under `plugin/` or `build/`, and the root build files such as `justfile`, which DEC-0006 decision 3b does not name) or c;
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
4. **Router: open one record per ticket** in the tracker and store the ticket text in it, then release the ticket to the worker only on the owner's word. The router edits nothing in the repository and claims no ticket.
5. **Worker: build the released ticket by its kind**, then report to the router the pull request, its head commit, what was run and its "Left unclear".
   - **Kind a**: built inline; the owner verifies each changed concept in the worker session, by structured question or on a review page private to the owner, the answers kept as a fragment (SDR-0022); CI's lint is the check. No router review. Several such changes may share one pull request.
   - **Kind c**: settled with the owner first (step 1); what it writes in `knowledge/` is then built as kind a.
   - **Kind b**: through the agent workflow `okf-layer-ticket` (`.claude/workflows/okf-layer-ticket.js`), which carries out the [Building with agents](/base/doctrine/building-with-agents.md) doctrine: one ticket per run, launched only after the owner's written message naming that ticket (see Warnings). The ticket lives in its tracker record, so the worker first writes it to a ticket file and the context common to every ticket to a common file, and passes `{ ticket, ticketPath, commonPath, bead, continueBranch? }` (the ticket's id, the two files, its tracker record and, to resume an interrupted builder, the branch holding its WIP commit). The workflow runs these stages:
     1. *Pre-flight*: an agent reads the ticket against the code and flags false premises, ambiguities and decisions that belong to the owner.
     2. *Builder*: works in a worktree, proves each criterion (revert → red → restore), pastes the output into the PR body and opens the PR as a draft. It lists what the ticket left unclear and the reading it took, in a "Left unclear" section of the PR body.
     3. *Review*: two reviewers with fresh context, without the builder's report, one per lens: correctness (the diff does what the ticket says, without contradicting the decisions the ticket or the common context names, and without regressions) and tests (each criterion's check would fail if the change were reverted). They challenge the ticket as well as the diff: a finding about the ticket itself (a criterion that is wrong, missing or contradicts a decision) starts with "Ticket:" and names the ticket's file. Each labels its findings blocking, to fix or nit. Each reviewer records the PR head commit it read; the workflow returns it as `reviewed_sha` when every reviewer of the last round read the same one, and `sha_mismatch` when they did not.
     4. *Classification*: one more agent with fresh context reads the ticket's bar and every finding of the round, not the PR, and rules which ones the bar makes blocking, whatever their label ([Building with agents](/base/doctrine/building-with-agents.md), principle 7). Only its blocking findings force a round of fixes. If it gives no ruling for every finding, the workflow falls back on the reviewers' labels and returns `classifier_failed`, and the worker classifies the findings itself.
     5. *Fixes*: at most two rounds; if that is not enough, the ticket goes back to the owner.

     Two more entries reuse the same stages. `fix: { pr, branch, findings }` starts at the fixes, with findings the router's verdict, the worker or the owner classified as blocking, then reviews and classifies again. `rebase: { pr, reviewed_sha, files }` runs only one reviewer with fresh context on a PR rebased after its review: with `git range-diff` it checks that the rebase changed only the conflicting files, and only to reconcile them with main, and it returns the new head as `reviewed_sha` if so, or `null` with its findings.
6. **Router: review a code change before its merge**, on the pushed head commit the worker reported. It runs the change on a bundle outside the repository, and when the change builds something a person uses (a page, an Obsidian vault) it also opens that output in the tool that reads it ([Building with agents](/base/doctrine/building-with-agents.md), principle 12). Its verdict is a comment on the pull request naming the commit, what it ran, what it opened and what it did not; it sends the worker a one-line pointer to that comment. A later push, a fix round or a rebase, needs a new verdict.
7. **Worker: merge on the owner's word**, given in the worker session: `gh pr merge <pr> --squash --match-head-commit <sha>`, with the head the router's verdict names, which refuses if the head moved after that review (then the router reviews again). Close the tracker record citing the pull request ([Building with agents](/base/doctrine/building-with-agents.md), principle 14). CI's run on `main` (`.github/workflows/ci.yml`) is the check of the merged main. When another PR of the layer merged first and this one has to be rebased (they edit the same text files, such as `log.md`), run the workflow with `rebase`, and merge with the `reviewed_sha` it returns once the router has given its new verdict. When the layer's tickets named human-verified concepts, the owner verifies them again once they are on main, and main stays red at `--strict` only until then. Pending nits go to a single follow-up record.
8. **Merge the layer before the next one.** The agents' worktrees branch off `origin/main`: a layer not on `origin/main` is invisible to the next one. Before the router releases the next layer, the router launches one fresh-context reviewer, until a decision names another session, that reads the layer's merged diff as a whole (`git diff <layer start>..origin/main`) for contracts split across tickets, names that collide and a ticket that assumed another's behaviour; a finding becomes a record of its own.

# Warnings

- An agent's report is a claim: the state is read from the PR and from the output of the checks, not from the answer (which may arrive truncated).
- A code change is never built inline. Pull request #133 was built inline with no reviewer and reviewed by reading and running a script only; tests, lint and CI passed, and two defects of the page it built reached main that only opening the page would have shown ([DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md), worked examples).
- Launching an agent workflow requires a written message from the owner that names the tickets; an approval given through a question dialog is not enough. A launch that passed only the ticket's id, with no ticket file, common file or written message, stopped at pre-flight (okf-1lj.3, `wf_d3b4fa24-1fe`).
- Reviewers and builders never run a recipe that starts sessions or other long-lived processes (`just sessions`, `just router`, `just worker`); they prove it by dry run (`just --dry-run sessions`) and by throwaway names in a scratch directory. In a fix round of pull request #137 a reviewer ran `just sessions` for real, though the ticket forbade it.
- `just sessions` needs `hc` on `PATH`, hc's server running (`hc server start`) and `claude` on the caller's `PATH`, which it hands to the sessions it starts. It sees only sessions hc runs under the two names: a session started by hand with `just router` or `just worker` is not seen, and a second one is started.
- An agent only stops processes it started itself, never by process name.
- `just hooks` installs the repository's pre-commit hook (`.githooks/pre-commit`) in a clone; it refuses a commit whose staged root copies or Obsidian setup are stale, and every worktree of that clone shares it.
- `just test` writes its scratch files to a directory of its own per run, but the exporters write `dist/` in the checkout, so two runs in one checkout collide. With tickets in parallel, only the builder runs `just test`; reviewers read the output pasted in the PR, and the worker runs it only after the agents finish.
- Resuming a workflow reruns the agents after the first change: to continue a half-finished run, pass its state (PR, branch, stage) as the starting point.

# Rollback

Each ticket is its own PR: revert the merge of the affected PR. If a layer already has dependent tickets merged, revert in reverse layer order.

# Related

* [DEC-0006: Two sessions maintain this repository, a router that plans and reviews and a worker that builds](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md)
* [Building with agents](/base/doctrine/building-with-agents.md)
* [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md)
