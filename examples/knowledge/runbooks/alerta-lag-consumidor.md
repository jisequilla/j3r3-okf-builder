---
type: Runbook
title: Alerta de lag en consumidor de pagos
description: Pasos cuando el consumer group de pagos supera 10k mensajes de lag.
tags: [runbook, oncall]
status: draft
stale_after: 2026-01-01T00:00:00Z
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T16:00:00Z }
verified:
  - { by: process:nightly-check, at: 2026-10-29T02:00:00Z }
---

# Disparador

Alerta `KafkaConsumerLagHigh`. Ver [ADR-0001](/decisiones/ADR-0001-adoptar-kafka.md).
