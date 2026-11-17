---
type: Knowledge Fragment
title: 2026-11-17 · The maintenance harness, two sessions and three kinds of change
description: The owner's answers of 2026-11-15 and 2026-11-17 on how this repository is maintained, a router session that plans and reviews, a worker session that builds, three kinds of change each with its own review, CI as the check after a merge and what the router's review of a code change includes, distilled into DEC-0006, which supersedes DEC-0002.
tags: [fragment, process, agents, review]
status: draft
occurred_at: 2026-11-17
origin: Claude Code session okf-router-session in this repository, on 2026-11-15 and 2026-11-17
participants: [human:jisequilla, okf-builder/claude-opus-5-5, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "68bc86e817813cc2afef611682490de525337826" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-17T21:22:01Z }
---

# Record

## What the owner asked for

On 2026-11-15, after the router session's review of pull request #133 found two defects that the builder's own checks and CI had passed, the owner typed in the router session (free text, context for the questions):

> ok this was a good thing i that we review the PR before merge, i think i we should make this flow a permantent one, also how to start both sessions, with a just recipie and have a system promt for both sessions, like a small harness for maintaninance over the okf builder, the rourter sessions plan distributes the work to the worker session and thas a final pr review to make sure of the implementation, and the worker sessions should alwasy implement either with dynamic workflows or a subagent and an adversirial review with in ti's session either within the workflow or with the worker session, what do you think?

## How the worker builds a ticket

Structured question, 2026-11-15: "How must the worker session build a ticket? Today DEC-0002 already asks for a builder plus fresh-context reviewers, but the beads let the worker choose 'inline', and PR #133 was built with no reviewer." Options: "Workflow for plugin changes (Recommended)", "Always workflow", "Worker chooses, review fixed". The owner's answer: "Workflow for plugin changes (Recommended)". The chosen option's description: "Any change under plugin/ or build/ (feat, fix) runs through the okf-layer-ticket workflow: builder in a worktree, adversarial reviewers with fresh context who also challenge the ticket. Docs-only PRs in knowledge/ may be inline, since you verify those concepts yourself."

## Where the harness lives

Structured question, 2026-11-15: "Where should the two-session harness live: the 'just router' and 'just worker' recipes and the two system prompt files?" Options: "Checked into the repo (Recommended)", "Local only". The owner's answer: "Checked into the repo (Recommended)". Its description: "Recipes in the justfile, prompts as files in the repo (for example build/sessions/router.md and worker.md), each a few lines pointing at the runbook. Versioned, reviewed like everything else, visible to anyone who clones."

## How the knowledge base records the flow, first answer

Structured question, 2026-11-15: "How should the knowledge base record the two-session flow (router plans and reviews before merge, worker builds with reviewers)? DEC-0002 says 'the main session judges and does not implement' and has no pre-merge review by a second session." Options: "New decision + runbook (Recommended)", "Supersede DEC-0002", "Runbook only". The owner's answer: "New decision + runbook (Recommended)". Its description: "A new DEC-0006 that builds on DEC-0002 without superseding it: two named sessions, the worker rule, the router's probe review before merge, with a worked example from PR #133. The build-in-layers runbook gains the steps. You verify both."

## Where the router's verdict is kept

Structured question, 2026-11-15: "Where should the router's review verdict on a PR be kept? Today it goes only as a message between the two sessions." Options: "Comment on the PR (Recommended)", "Message only", "Bead comment". The owner's answer: "Comment on the PR (Recommended)". Its description: "The router posts its verdict as a comment on the GitHub PR (findings, what was run, what was not) and sends the worker a one-line pointer. Durable and visible at merge time. It means this session writes to GitHub, which it has not done so far."

## The contradiction the worker found

On 2026-11-17 the worker session found that the first plan's point 3, a change only under `knowledge/` built inline, contradicts DEC-0002 decisions 3 and 5, and stopped before writing. The router asked three questions; the owner asked for them to be explained, the router explained them in plain words, and the owner typed (free text, context for the questions):

> ok i understand now the problem and i agree for small changes i can verify in workre session and we do not need to run the whole cerremony, since it will generate a lot of friction one simple change, also we need to think deeper about the workflow, i mean it is ok to make a change i need to verify it, but we should need a pr a merge and 3 reviews for this small type of changes, we should be able to focus on bringin value with order, what do you think?

## Three kinds of change, replacing DEC-0002

Structured question, 2026-11-17: "Should the harness decision sort work into three kinds, each with its own level of review, and replace DEC-0002 with that single rule?" Options: "Three kinds, replace DEC-0002 (Recommended)", "Two kinds only", "Think it through first". The owner's answer: "Three kinds, replace DEC-0002 (Recommended)". The chosen option's description: "Small knowledge fix: worker inline, you verify, CI lint, no router review, several fixes may share one PR. Code change (plugin/, build/): workflow with reviewers, router runs it and opens the output, verdict on the PR. Decision or standard change: settled with you first. DEC-0002 is superseded by this one rule."

## The check after a merge

Structured question, 2026-11-17: "After a merge, who checks that main still passes before the ticket closes?" Options: "CI on main is enough (Recommended)", "Worker reruns on main". The owner's answer: "CI on main is enough (Recommended)". Its description: "The automatic run on main after the squash merge counts; the decision names that CI job. No extra step for anyone."

## What the router's review of a code change includes

Structured question, 2026-11-17: "For code changes, what should the router's review include?" The owner answered by asking for more detail; after it, the router asked again: "For a code change, when the router reviews the PR before your merge, should it only run the change on a test bundle, or also open what it builds (for example the viewer page in a browser) when the change produces something a person looks at?" Options: "Run it and open the output (Recommended)", "Run it only". The owner's answer: "Run it and open the output (Recommended)". Its description: "When the change builds something a person uses (a page, an Obsidian vault), the router also opens it and clicks through it, and says so in its verdict. Would have caught the page bugs of PR #133. A few minutes more, only for such changes."

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| What the owner asked for | — | context | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| How the worker builds a ticket | addition | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| Where the harness lives | addition | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| How the knowledge base records the flow, first answer | — | replaced by the answer of 2026-11-17 | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| Where the router's verdict is kept | addition | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| The contradiction the worker found | — | context | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| Three kinds of change, replacing DEC-0002 | update | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| The check after a merge | update | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
| What the router's review of a code change includes | addition | applied | [DEC-0006](/base/decisions/DEC-0006-two-sessions-three-kinds-of-change.md) |
