---
type: Open Question
title: Retention of refund events
description: How long refund events must stay on the Kafka bus, given that refunds can be disputed long after the payment.
tags: [question, payments, messaging]
status: draft
owner: human:maria
question_status: open
asked_in: /fragments/2026-11-02-refund-events-review.md
blocks: [/base/decisions/ADR-0001-adopt-kafka.md]
review_on: 2031-11-01
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T11:58:35Z }
sources:
  - { id: sync, resource: /fragments/2026-11-02-refund-events-review.md, title: "Fragment: payments sync on refund events" }
---

# Question

How long must refund events stay on the Kafka bus?[^sync]

# Why it matters

[ADR-0001](/base/decisions/ADR-0001-adopt-kafka.md) sets 7 days of retention for payment events. If refunds can be disputed later than that, a refund event could be gone before the dispute that needs it.

# What is known

Refunds can be disputed long after the payment. The dispute window finance works with is not known yet.

# Answer

[^sync]: Fragment: payments sync on refund events
