---
type: Architecture Decision
title: "ADR-0001: One approver per refund"
description: Every refund is approved by one person of the refunds team, whatever its amount.
tags: [adr, refunds]
status: draft
adr_id: ADR-0001
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/test, at: 2026-11-09T16:00:00Z }
---

# Context

Refunds were approved by whoever was on shift, with no rule.

# Decision

We approve every refund with one approver of the refunds team, whatever its amount.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Two approvers above a threshold | Fewer large mistakes | Slower refunds | The volume of large refunds did not justify it |

# Consequences

- Positive: refunds are fast.
- Negative: a large refund rests on one person.
