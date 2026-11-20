---
type: Knowledge Fragment
title: 2026-11-20 · Verification of the build-in-layers runbook and the doctrine after the two-session flow, in a structured question
description: The structured question that asked the owner to verify the runbook Build a change in layers and the doctrine Building with agents after they were rewritten to describe the merged two-session flow (tracker item okf-m41.3), and the owner's answers confirming both at the version named.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-20T16:31:41Z
origin: Claude Code session in this repository (okf-worker-session)
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "7bdcdef077ac230eba805eb9421c25284a60e62a" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-20T16:31:41Z }
---

# Record

## The runbook Build a change in layers

On main at commit 7bdcdef, before the commit of tracker item okf-m41.3. Structured question:

> Do you verify the runbook 'Build a change in layers' (knowledge/base/runbooks/build-in-layers.md) at generated.at 2026-11-20T16:29:15Z? Full text is in the file; the preview shows what changed.

The preview listed the changes: the Trigger names both sessions, cites DEC-0006 and says how to start them (`just sessions`, `hc attach`, `just router` and `just worker`); steps 1 to 4 are the router's, and a ticket names its kind, with the root build files such as `justfile` in kind b; step 5 is the worker's, by kind, with the ticket and common files written from the bead, the reviewers' "Ticket:" findings and the worker's report; step 6 is the router's review of the pushed head; step 7 the merge in the worker session on the owner's word; step 8 the layer on `origin/main` before the next is released; and the Warnings gain pull request #133, the launch that passed only the ticket's id, the reviewer that ran `just sessions`, and what `just sessions` needs.

Options: "Yes, verified" (described as: "The runbook reads true as written; it becomes status: stable with your verification recorded"), "No, change it" (described as: "Say what is wrong in the notes; I rewrite and ask again"). The owner's answer: "Yes, verified".

## The doctrine Building with agents

In the same structured question:

> Do you verify the doctrine 'Building with agents' (knowledge/base/doctrine/building-with-agents.md) at generated.at 2026-11-20T16:29:15Z?

The preview showed principle 1 rewritten as "The session that judges does not build", with the router and the worker, PR #75 stated as evidence instead of a rule, and pull request #133 as new evidence; the source, Related link and footnote pointing at DEC-0006 instead of DEC-0002; principles 5 and 11 unchanged.

Options: "Yes, verified" (described as: "It becomes status: stable with your verification recorded"), "No, change it" (described as: "Say what is wrong in the notes; I rewrite and ask again"). The owner's answer: "Yes, verified".

Both concepts' `generated.at` was 2026-11-20T16:29:15Z when the answers were applied.

## The runbook again, after step 8 names the router

On branch `docs/okf-m41-3` (pull request #138), at commit 2d15adb before the next commit. The owner, answering the PR's first "Left unclear" item in the router session ("Name the router for now"), chose the router to launch the fresh-context review of a layer's merged diff, worded to hold only until a decision says otherwise. In the worker session the owner chose the wording "Until decided otherwise" over "For now, the router". Structured question:

> Do you verify the runbook 'Build a change in layers' (knowledge/base/runbooks/build-in-layers.md) at generated.at 2026-11-20T16:39:09Z, on branch docs/okf-m41-3 (PR #138)? Only step 8 changes from the version you verified at 16:29:15Z.

The preview showed step 8 before ("Before the router releases the next layer, one fresh-context reviewer reads the layer's merged diff as a whole ...") and after ("Before the router releases the next layer, the router launches one fresh-context reviewer, until a decision names another session, that reads the layer's merged diff as a whole ...").

Options: "Yes, verified" (described as: "Record your verification, status stable, keep this question and answer in the okf-m41.3 fragment, log.md entry, push to PR #138"), "No, change it" (described as: "Stays draft; say in the notes what step 8 should say"). The owner's answer: "Yes, verified".

The runbook's `generated.at` was 2026-11-20T16:39:09Z when the answer was applied.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The runbook Build a change in layers | — | verified | [Build a change in layers](/base/runbooks/build-in-layers.md) |
| The doctrine Building with agents | — | verified | [Building with agents](/base/doctrine/building-with-agents.md) |
| The runbook again, after step 8 names the router | — | verified | [Build a change in layers](/base/runbooks/build-in-layers.md) |
