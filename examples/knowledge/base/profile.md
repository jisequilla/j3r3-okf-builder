---
type: Domain Profile
title: Domain Profile of Demo Payments
description: The taxonomy of the demo payments bundle, on top of the built-in Domain Profile; one local type for payments meetings, one family for open questions, one rule and its aliases.
tags: [profile, taxonomy]
status: draft
extends: []
types:
  Payments Meeting:
    extends: Knowledge Fragment
    description: A meeting of the payments team, recorded as it happened
    fields:
      team: { type: string, level: warn, note: The team that held the meeting }
      kind: { type: enum, values: [weekly-sync, follow-up], note: Which of the team's meetings it was }
      decisions_taken: { type: integer, level: warn, note: How many decisions the meeting took }
families:
  /base/questions/:
    types: [Open Question]
    required: [tags]
forbidden:
  internal_notes: { reason: Internal notes stay out of the bundle }
fixed:
  okf_lang: { value: en, level: warn }
by_type: {}
rules:
  - { name: distilled-payments-meeting-names-team, when: { type: Payments Meeting, distillation_status: distilled }, require: [team], level: warn }
validator: []
questions:
  - { question: "How long must refund events be kept?", concept: /base/questions/refund-event-retention.md }
aliases:
  types: { Reunión de pagos: Payments Meeting }
  fields: { equipo: team }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T18:00:00Z }
sources:
  - { id: refund-review, resource: /fragments/2026-11-02-refund-events-review.md, title: "Payments sync: refund events on the Kafka bus" }
  - { id: domain-profile, resource: https://github.com/jisequilla/j3r3-okf-builder/blob/main/standard/OKF-STANDARD.md, title: "OKF standard §4.1: Domain Profile" }
---

# What this bundle holds

The knowledge of a fictional payments platform: its decisions, runbooks and open questions under `base/`, and the meetings that produced them under `fragments/`. It extends no shared profile: the built-in Domain Profile is its only other layer[^domain-profile].

# Types

## Payments Meeting

The payments team meets every week, and what a reader of a fragment wants first is which team decided what[^refund-review]. A `Payments Meeting` is a `Knowledge Fragment`, so it keeps every fragment check, and adds:

- `team`: the team that held the meeting, as the team names itself. Its local name `equipo` is read as `team`.
- `kind`: `weekly-sync` or `follow-up`, the two meetings the team holds.
- `decisions_taken`: how many decisions the meeting took, an integer.
- Rule `distilled-payments-meeting-names-team`: once a meeting is distilled, its concepts are traced back to it by team, so a distilled meeting names its team.

`Reunión de pagos` is a local name for `Payments Meeting`.

# Keys for every concept

- `internal_notes` is forbidden: notes meant for the team only stay out of the bundle.
- `okf_lang`, where a concept carries it, is `en`: the bundle is written in English.

# Families

## /base/questions/

Open questions only, so the list of what the team does not know stays a list of questions. Each one carries `tags`, which group the questions by area.

# Questions

The open question on refund retention is answered at [its own concept](/base/questions/refund-event-retention.md).
