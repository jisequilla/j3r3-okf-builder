---
type: Domain Profile
title: Domain Profile of okf-builder
description: The taxonomy of this repository's own knowledge bundle, on top of the built-in Domain Profile; one local type, Doctrine, for how the repo works, with the evidence that taught each principle.
tags: [profile, taxonomy, doctrine]
status: stable
extends: []
types:
  Doctrine:
    description: How the repo works, as principles, each with its reason and the evidence that taught it
    directory: /base/doctrine/
    fields:
      owner: { type: string, level: warn, note: Who answers for the doctrine (ADR-0027) }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-05T04:06:24Z }
verified: { by: human:jisequilla, at: 2026-11-10T22:38:51Z }
sources:
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md, title: "ADR-0028: Where things go" }
  - { id: session, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 · Building the knowledge audit and v0.9.0 with agent workflows" }
---

# What this bundle holds

The knowledge of the OKF standard and the okf-builder plugin: decisions, systems, runbooks, policies, references and roles under `base/`, in the built-in types, plus one local type for how the repo works. It extends no shared profile.

# Types

## Doctrine

How the repo builds with agents is practice that changes as each run teaches something, and it needs the evidence that taught it[^adr-0028]. No built-in type holds that: an Architecture Decision is never edited, a Policy states rules without their reasons and evidence, and a Runbook is a procedure. A Doctrine is a set of principles, each with its statement, why it holds and its evidence (a link to an ADR, a fragment or a PR), edited in place as practice teaches; new practice enters as a fragment and is distilled with `okf-distill`[^session]. It extends no built-in type, so it carries only the spec's fields and its own.

- `owner`: who answers for the doctrine and approves its changes, a string as for the other operational types (ADR-0027).

[^adr-0028]: ADR-0028, decision 7.
[^session]: The 2026-11-04 session, "Where things go".
