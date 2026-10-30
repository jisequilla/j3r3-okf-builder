---
type: Architecture Decision
title: "ADR-0001: Adoptar Kafka para eventos de pago"
description: Kafka sustituye a RabbitMQ como bus de eventos de pago.
tags: [adr, mensajeria]
status: stable
adr_id: ADR-0001
decision_status: accepted
generated: { by: human:jisequilla, at: 2026-10-30T15:00:00Z }
verified: { by: human:jisequilla, at: 2026-10-30T15:30:00Z }
sources:
  - id: bench
    resource: docs/benchmarks/kafka-vs-rabbit.md
    title: Benchmark interno
    author: team:platform
    last_modified: 2026-09-15T00:00:00Z
---

# Contexto

El [servicio de pagos](/systems/pagos-api.md) necesita retención de 7 días.[^bench]

# Decisión

Adoptamos Kafka.

[^bench]: Benchmark interno
