---
type: Runbook
title: Payments dead-letter replay
description: Steps to replay the payment events parked on the payments dead-letter topic once their consumer is fixed.
tags: [runbook, oncall, messaging]
status: draft
owner: team:payments
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T22:32:48Z }
---

# Trigger

Messages on the `payments.dlq` topic after a consumer failure. The bus is the one of [ADR-0001](/base/decisions/ADR-0001-adopt-kafka.md).

# Diagnosis

1. Read the error header of the first parked message.
2. Confirm that the consumer that failed is fixed and deployed.

# Resolution steps

1. Replay `payments.dlq` into `payments` from its oldest offset.
2. Watch the consumer lag until it is back under 10k messages ([Payments consumer lag alert](/base/runbooks/consumer-lag-alert.md)).

# Escalation

| Level | Who | When |
|---|---|---|
| 1 | Payments on-call | The replay fails twice |
