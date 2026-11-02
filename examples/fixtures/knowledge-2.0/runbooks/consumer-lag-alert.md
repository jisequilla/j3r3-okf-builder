---
type: Runbook
title: Payments consumer lag alert
description: Steps when the payments consumer group exceeds 10k messages of lag.
tags: [runbook, oncall]
status: draft
stale_after: 2026-01-01T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:44Z }
verified:
  - { by: process:nightly-check, at: 2026-10-29T02:00:00Z }
---

# Trigger

Alert `KafkaConsumerLagHigh`. See [ADR-0001](/decisions/ADR-0001-adopt-kafka.md).
