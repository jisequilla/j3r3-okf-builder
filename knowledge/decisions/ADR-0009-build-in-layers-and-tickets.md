---
type: Architecture Decision
title: "ADR-0009: Build multi-stage changes in layers and delegated tickets"
description: Changes that touch several layers of the repo are split into verifiable tickets that agents build in isolated worktrees, and the main session only judges, verifies and merges.
tags: [adr, process, agents]
status: draft
adr_id: ADR-0009
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

Some changes cut across the whole repo: the standard, the scripts, the skills and `knowledge/` itself (for example, translating the profile or renaming its vocabulary). Done in a single conversation, they mix decision and implementation, skip verification stages and leave the work half done when the context is compacted. A subagent only knows what its brief says, and its "done" report is a claim, not a proof.

# Decision

We adopt a pattern of building in layers and tickets, detailed in the runbook [Build a change in layers](/runbooks/build-in-layers.md):

1. **Layers in dependency order.** What the owner decides (ADR, vocabulary, glossary) goes first, and is merged and pushed to `origin/main` before launching the layers that depend on it.
2. **One ticket per unit of work**, precise by example: input → expected output table, closed list of files, pattern to copy as `file:line` and exact verification commands. A ticket that cannot be written this way is not ready to delegate.
3. **The main session judges and does not implement.** Each ticket goes through pre-flight, a builder in a worktree with a draft PR, one or two reviewers with fresh context (without the builder's report) and at most two rounds of fixes.
4. **Verification in layers, none reliable on its own:** the builder proves each acceptance criterion (revert → red → restore), the reviewers try to break the diff, and the main session reruns `make test` and `make lint` on the merged main before closing.
5. **Prose is verified mechanically too.** Since it has no tests, each prose ticket carries a check (for example, a grep for leftover vocabulary that fails on a planted file) and a meaning-drift review pass against the glossary.
6. **Tracking independent of the tracker.** Each ticket has its work record (in the owner's environment, a local `bd` bead), which is closed only after the merge and with the PR cited. The repo does not depend on any tracker.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Everything in the main session | No coordination cost | Mixes judgment and implementation; stages get skipped; fragile under compaction | Does not scale to changes of ~150 files |
| Free fan-out of subagents without tickets | Fast | Terminology drift; no acceptance criteria; reports are accepted as proof | Verification is left to the implementer |
| Copy the full tooling of another repo (wave generators, mutation runs, delegation log) | Proven in another context | Disproportionate weight for a few tickets | KISS: it will be added if the ticket volume justifies it |

# Consequences

- Positive: each stage leaves a reviewable PR; large changes survive compaction; any agent, on any platform, can follow the same procedure by reading the runbook.
- Negative / accepted debt: more ceremony per change; it only pays off for multi-stage changes, so small fixes are still done inline.
- Follow-up actions: apply the pattern to migrating the repo to English.

# Related

* [Build a change in layers](/runbooks/build-in-layers.md)
* [Rules for agents working in this repo](/policies/agents-in-this-repo.md)
* [ADR-0008: dogfooding](/decisions/ADR-0008-dogfooding.md)
