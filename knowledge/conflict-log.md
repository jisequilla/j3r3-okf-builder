---
type: Conflict Log
title: Conflict log
description: Every conflict found while distilling a fragment into this bundle, with its resolution, state and who decided.
tags: [conflicts, distillation]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T19:45:00Z }
---

# How it is used

A conflict comes out of distilling a fragment and is closed by a person ([ADR-0015](/decisions/ADR-0015-fragment-format-and-conflict-log.md)). States: `open` · `proposed` · `resolved` · `dismissed` (a misunderstanding).

# Conflicts

| ID | Source | Description | Kind | Resolution | State | Decided |
|---|---|---|---|---|---|---|
| C-001 | [KDD bundle review](/fragments/2026-10-31-kdd-bundle-review.md) | The KDD bundle uses `Knowledge Fragment` with `origin` and `distillation_status`; ADR-0012 uses `Fragment` with `medium` and `participants` | Contradiction with an accepted ADR | Merge: the KDD format plus `participants`; ADR-0015 supersedes ADR-0012 | resolved | human:jisequilla |
| C-002 | [KDD bundle review](/fragments/2026-10-31-kdd-bundle-review.md) | The KDD bundle keeps one conflict register; ADR-0012 lists conflicts in each fragment | Contradiction with an accepted ADR | One `Conflict Log` per bundle (ADR-0015) | resolved | human:jisequilla |
| C-003 | [KDD bundle review](/fragments/2026-10-31-kdd-bundle-review.md) | The KDD bundle expects `okf-fragment`, `okf-distill` and `okf-review`; ADR-0012 folds fragment capture into `okf-capture` | Contradiction with an accepted ADR | Three separate skills; the M365 agent leaves out `okf-migrate` (ADR-0015) | resolved | human:jisequilla |
