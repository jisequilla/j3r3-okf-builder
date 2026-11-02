---
type: Architecture Decision
title: "ADR-0005: generated required and verified only by people"
description: "The profile requires generated on every concept and forbids an agent from writing verified with a human: actor."
tags: [adr, trust]
status: stable
adr_id: ADR-0005
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
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
