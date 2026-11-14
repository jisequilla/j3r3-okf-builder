---
type: Standard Decision
title: "SDR-0005: generated required and verified only by people"
description: "The profile requires generated on every concept and forbids an agent from writing verified with a human: actor."
tags: [adr, trust]
status: deprecated
decision_id: SDR-0005
formerly: ADR-0005
decision_status: superseded
superseded_by: /base/decisions/standard/SDR-0018-verification-recorded-by-question.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
---

# Context

OKF v0.2 derives the trust level from `verified`: any `human:` actor raises the concept to *human-reviewed*. If an agent wrote it, the signal would lose all its value.

# Decision

1. `generated: { by, at }` is required in the profile (the spec leaves it optional). Actor: `human:<id>` if the person dictates the content, `okf-builder/<model>` if the agent synthesizes it.
2. No skill or script adds `verified`. Only after the person's explicit confirmation is `verified: { by: human:<id>, at }` added and the concept moved to `status: stable`.
3. Every concept starts in `status: draft`.

# Consequences

- Positive: the derived trust is reliable; what a person has looked at can be told apart.
- Negative: friction when creating (one more human step); that is the intended cost.
