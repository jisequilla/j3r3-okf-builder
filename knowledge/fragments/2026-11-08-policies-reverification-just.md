---
type: Knowledge Fragment
title: 2026-11-08 · Re-verification of the two policies after the switch to just
description: The owner's answers to two structured questions confirming the two policies at commit 65f9df7, after their controls were changed to name the just recipes (ADR-0035) and the conformance policy stopped claiming a CI.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-08
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "65f9df75c01e7aeb55b9bb6efb9513e5ad73807d" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:39:09Z }
---

# Record

Switching the build to just (okf-cby, ADR-0035) changed one line in each policy; in a structured question the owner also chose to drop the conformance policy's claim that lint runs in CI, since this repository has no CI. After the edit, committed as `65f9df7`, the agent asked the two questions below in the session's question tool, one dialog, and the owner answered at 2026-11-08T21:39:09Z. Kept verbatim.

**Question 1** (header "Agents rule")

> Re-verify "Rules for agents working in this repo" (knowledge/base/policies/agents-in-this-repo.md) at commit 65f9df7, generated.at 2026-11-08T21:34:38Z? The only change since your last verification is rule 4, which now reads: "4. Finish with `just test` (code) and `just lint` (knowledge)." Everything else is as you verified it at 14:12:07Z.
>
> Options: "Confirm this version" (Record verified by human:jisequilla now, keep status: stable.) · "Needs changes" (Leave it unverified. Tell me what to change.)

**Answer**: "Confirm this version"

**Question 2** (header "Conformance")

> Re-verify "Conformance with profile knowledge/3.0" (knowledge/base/policies/okf-conformance.md) at commit 65f9df7, generated.at 2026-11-08T21:36:30Z? The only change is its controls line, which now reads: "`just lint` (`okf_lint --strict` on `knowledge/` and `examples/knowledge`) after every change; `okf-capture` always finishes with lint." That is make → just, and "in CI" dropped.
>
> Options: "Confirm this version" (Record verified by human:jisequilla now, keep status: stable.) · "Needs changes" (Leave it unverified. Tell me what to change.)

**Answer**: "Confirm this version"

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Rules for agents working in this repo | — | verified | [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md) |
| Conformance with profile knowledge/3.0 | — | verified | [Conformance with profile knowledge/3.0](/base/policies/okf-conformance.md) |
