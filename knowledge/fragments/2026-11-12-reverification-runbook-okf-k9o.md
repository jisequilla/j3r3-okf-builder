---
type: Knowledge Fragment
title: 2026-11-12 · Re-verification of the runbook after okf-k9o
description: The owner's answer to a structured question confirming Build a change in layers at generated.at 2026-11-12T21:34:01Z, after okf-k9o gave it the bar classifier, the human-verified concepts a ticket names, and the fix and rebase entries of the workflow.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-12T21:41:17Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "2fa81adde8702056a0a6b2643df8a12cf588a5ad" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-12T21:41:17Z }
---

# Record

okf-k9o changed [Build a change in layers](/base/runbooks/build-in-layers.md), which human:jisequilla had verified on 2026-11-11, on branch `okf-k9o` from `2fa81ad`. Before the PR, the agent summarised the four changes and asked in the session's question tool. Kept verbatim.

**Question** (header "Runbook")

> Do you verify 'Build a change in layers' (knowledge/base/runbooks/build-in-layers.md) at generated.at 2026-11-12T21:34:01Z? Since your verification of 2026-11-11 it changed in four places. (1) Step 3: a ticket names the human-verified concepts it must edit; the bar exempts VERIFIED_STALE on them and nothing else, and you verify them again after the merge, once per layer. (2) Step 5.4, new: one fresh agent reads the bar and the round's findings, not the PR, and rules which are blocking whatever their label. If it gives no ruling for every finding, the workflow falls back on the labels and returns classifier_failed. (3) Step 5, new entries: fix {pr, branch, findings} starts at the fixes; rebase {pr, reviewed_sha, files} runs one fresh reviewer that checks with git range-diff that the rebase changed only the conflicting files, and returns the new reviewed_sha or null. (4) Step 6: a PR rebased after another of its layer merged goes through the rebase entry, and main stays red at --strict only until you re-verify the named concepts.
>
> Options: "Verify" (I record your answer verbatim as a fragment (ADR-0033) in this same PR, and the runbook goes back to stable with your verification, so main never goes red. Right if the four changes read correctly to you.) · "Read it first" (You open the file on the branch and answer later. The PR stays draft with lint --strict red on this warning until you do. Right if you want to read the steps in full rather than this summary.) · "Change something" (Write in the note what doesn't fit. I fix it on the branch and ask again, and the runbook stays draft meanwhile. Right if any of the four changes is wrong or unclear.)

**Answer**: "Verify"

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Question | — | verified | [Build a change in layers](/base/runbooks/build-in-layers.md) |
