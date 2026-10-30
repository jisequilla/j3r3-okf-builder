---
type: Architecture Decision
title: "ADR-0001: Adopt Kafka for payment events"
description: Kafka supersedes RabbitMQ as the payment event bus.
tags: [adr, messaging]
status: stable
adr_id: ADR-0001
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:44Z }
verified: { by: human:jisequilla, at: 2026-10-30T15:30:00Z }
sources:
  - id: bench
    resource: docs/benchmarks/kafka-vs-rabbit.md
    title: Internal benchmark
    author: team:platform
    last_modified: 2026-09-15T00:00:00Z
---

# Context

The [payments service](/systems/pagos-api.md) needs 7-day retention.[^bench]

# Decision

We adopt Kafka.

[^bench]: Internal benchmark
