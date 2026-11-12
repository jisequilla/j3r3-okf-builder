---
type: Runbook
title: Refund retry
description: How the backlog of failed refunds is retried by hand until req-0042 ships.
tags: [runbook, refunds]
status: draft
owner: team:refunds
generated: { by: okf-builder/test, at: 2026-11-05T12:00:00Z }
sources:
  - { id: scoping, resource: /fragments/2026-11-05-scoping-call.md, title: "Scoping call of req-0042" }
---

# Trigger

A refund fails and lands in the backlog[^scoping].

# Resolution steps

1. Retry each failed refund by hand from the backlog.

[^scoping]: 2026-11-05 · Scoping call of req-0042, Refund retry.
