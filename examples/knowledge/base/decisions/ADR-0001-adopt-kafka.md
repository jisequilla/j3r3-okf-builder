---
type: Architecture Decision
title: "ADR-0001: Adopt Kafka for payment events"
description: Kafka supersedes RabbitMQ as the payment event bus.
tags: [adr, messaging]
status: stable
adr_id: ADR-0001
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-04T20:01:57Z }
verified: { by: human:jisequilla, at: 2026-10-30T15:30:00Z }
sources:
  - id: bench
    resource: docs/benchmarks/kafka-vs-rabbit.md
    title: Internal benchmark
    author: team:platform
    last_modified: 2026-09-15T00:00:00Z
  - id: refund-events
    resource: /fragments/2026-11-02-refund-events-review.md
    title: "2026-11-02 · Payments sync: refund events on the Kafka bus"
---

# Context

The [payments service](/base/systems/pagos-api.md) needs 7-day retention.[^bench]

# Decision

We adopt Kafka.[^refund-events]

[^bench]: Internal benchmark
[^refund-events]: 2026-11-02 · Payments sync: refund events on the Kafka bus
