---
type: Conflict Log
title: Conflict log
description: Every conflict found while distilling a fragment into this bundle, with its resolution, state and who decided.
tags: [conflicts, distillation]
status: draft
generated: { by: okf-builder/test, at: 2026-11-05T12:00:00Z }
---

# How it is used

A conflict comes out of distilling a fragment and is closed by a person. States: `open` · `proposed` · `resolved` · `dismissed` (a misunderstanding) · `carried` (carried up into the parent bundle, naming its row there). A carried row's Resolution names the parent's row and its path from this bundle's root, as code, never a link (`C-NNN` of `../../conflict-log.md`): links run down only.

# Conflicts

| ID | Source | Description | Kind | Resolution | State | Decided |
|---|---|---|---|---|---|---|
| C-001 | [Scoping call](/fragments/2026-11-05-scoping-call.md) | Ana says the refund API returns 200 for a refund still pending; Maria says finance reads every 200 as paid | sources disagree | | open | — |
