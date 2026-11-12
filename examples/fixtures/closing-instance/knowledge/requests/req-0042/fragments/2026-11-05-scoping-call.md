---
type: Knowledge Fragment
title: Scoping call of req-0042
description: The call that scoped the faster refund approvals of req-0042.
tags: [fragment, request]
status: draft
occurred_at: 2026-11-05
origin: scoping call of req-0042
participants: [human:test, human:maria, human:ana]
distillation_status: conflict
generated: { by: okf-builder/test, at: 2026-11-05T12:00:00Z }
---

# Record

## Refund window

Maria: customers have 30 days after the payment to ask for a refund.

## Dual approval

Ana: refunds above 500 EUR should need two approvers.

## Refund retry

Ana: the backlog of failed refunds is retried by hand until this request ships.

## Partial refunds

Maria: nobody knows yet who approves a partial refund.

## Pending refunds

Ana: the refund API answers 200 while a refund is still pending. Maria: finance reads every 200 as paid.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Refund window | Addition | applied | [Refund window](/base/domain/refund-window.md) |
| Dual approval | Addition | applied | [Dual approval](/base/domain/dual-approval.md) |
| Refund retry | Addition | applied | [Refund retry](/base/runbooks/refund-retry.md) |
| Partial refunds | Addition | applied | [Who approves partial refunds?](/base/questions/who-approves-partial-refunds.md) |
| Pending refunds | Conflict | open: C-001 | [Conflict log](/conflict-log.md) |
