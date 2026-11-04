---
type: Knowledge Fragment
title: "2026-11-02 · Payments sync: refund events on the Kafka bus"
description: A short fictional platform meeting on moving refund events to Kafka, which left open how long refund events must be kept.
tags: [fragment, payments, messaging]
status: draft
occurred_at: 2026-11-02
origin: Weekly payments platform sync (video call)
participants: [human:maria, human:tomas, okf-builder/claude-opus-5-5]
distillation_status: distilled
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T11:58:35Z }
---

# Record

**Refund events.** Tomás proposed publishing refund events on the same Kafka bus as payment events, following [ADR-0001](/base/decisions/ADR-0001-adopt-kafka.md). Nobody objected.

**Retention.** Payment events keep 7 days of retention. María said refunds can be disputed long after a payment, so 7 days may be too short for refund events; nobody knew the dispute window finance works with. María will find out.

**Action item.** Tomás opens the ticket to add a `refunds` topic.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Refund events on the Kafka bus, following ADR-0001 (confirms that Kafka is the event bus) | confirmation | applied | [ADR-0001](/base/decisions/ADR-0001-adopt-kafka.md) |
| How long must refund events be kept on the bus? (an open question) | addition | applied | [Retention of refund events](/base/questions/refund-event-retention.md) |
| Add a `refunds` topic (Tomás; an action item, filed in the team's tracker) | — | not distilled | tracker |
