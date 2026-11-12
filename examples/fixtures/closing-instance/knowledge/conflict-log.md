---
type: Conflict Log
title: Conflict log
description: Every conflict found while distilling a fragment into this bundle, with its resolution, state and who decided.
tags: [conflicts, distillation]
status: draft
generated: { by: okf-builder/test, at: 2026-11-09T16:00:00Z }
---

# How it is used

A conflict comes out of distilling a fragment and is closed by a person. States: `open` · `proposed` · `resolved` · `dismissed` (a misunderstanding) · `carried` (carried up into the parent bundle, naming its row there). A carried row's Resolution names the parent's row and its path from this bundle's root, as code, never a link (`C-NNN` of `../../conflict-log.md`): links run down only.

# Conflicts

| ID | Source | Description | Kind | Resolution | State | Decided |
|---|---|---|---|---|---|---|
| C-001 | [Closing of req-0042](/fragments/2026-11-09-closing-req-0042.md) | [Dual approval](/requests/req-0042/base/domain/dual-approval.md) asks two approvers above 500 EUR; [ADR-0001](/base/decisions/ADR-0001-one-approver-per-refund.md) keeps one | contradiction with an accepted ADR | | open | — |
| C-002 | [Closing of req-0042](/fragments/2026-11-09-closing-req-0042.md) | Carried up from C-001 of [req-0042's conflict log](/requests/req-0042/conflict-log.md): the refund API returns 200 for a refund still pending, and finance reads it as paid | sources disagree | | open | — |
