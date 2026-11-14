---
type: Domain Profile
title: Domain Profile of okf-builder
description: The taxonomy of this repository's own knowledge bundle, on top of the built-in Domain Profile; two local types, Doctrine for how the repo works, with the evidence that taught each principle, and Standard Decision for a decision about what the OKF standard says.
tags: [profile, taxonomy, doctrine]
status: stable
extends: []
types:
  Doctrine:
    description: How the repo works, as principles, each with its reason and the evidence that taught it
    directory: /base/doctrine/
    fields:
      owner: { type: string, level: warn, note: Who answers for the doctrine (SDR-0020) }
  Standard Decision:
    extends: Decision
    description: A decision about what the OKF standard says
    directory: /base/decisions/standard/
    prefix: SDR
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: [{ by: human:jisequilla, at: 2026-11-10T22:38:51Z }, { by: human:jisequilla, at: 2026-11-14T17:32:10Z }]
sources:
  - { id: adr-0028, resource: /base/decisions/DEC-0003-where-things-go.md, title: "DEC-0003: Where things go" }
  - { id: adr-0041, resource: /base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md, title: "SDR-0026: A decision is a Decision; Architecture Decision is one kind of it, each kind has its own folder, prefix and sequence, and a link inside a record follows a decision that moves" }
  - { id: session, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 · Building the knowledge audit and v0.9.0 with agent workflows" }
---

# What this bundle holds

The knowledge of the OKF standard and the okf-builder plugin: decisions, systems, runbooks, policies, references and roles under `base/`, in the built-in types, plus two local types: one for how the repo works and one for the decisions about the standard. It extends no shared profile.

# Types

## Doctrine

How the repo builds with agents is practice that changes as each run teaches something, and it needs the evidence that taught it[^adr-0028]. No built-in type holds that: an Architecture Decision is never edited, a Policy states rules without their reasons and evidence, and a Runbook is a procedure. A Doctrine is a set of principles, each with its statement, why it holds and its evidence (a link to an ADR, a fragment or a PR), edited in place as practice teaches; new practice enters as a fragment and is distilled with `okf-distill`[^session]. It extends no built-in type, so it carries only the spec's fields and its own.

- `owner`: who answers for the doctrine and approves its changes, a string as for the other operational types (SDR-0020).

## Standard Decision

26 of this bundle's 41 decisions are about what the OKF standard says (its format, layers, types, fields and the rules a bundle must follow), not about how a system is built, so the name `Architecture Decision` is wrong for them while its shape fits[^adr-0041]. A Standard Decision extends the built-in `Decision`, so it carries that type's fields and rules: `decision_status`, `supersedes`, `superseded_by`, `decision_id`, `formerly`, and a body that is never edited once accepted. It lives in `base/decisions/standard/` and numbers on its own sequence with the prefix `SDR`. A decision about how the repo works (build runner, releases, tickets, where files go) is a plain `Decision`, in `base/decisions/` with the prefix `DEC`; a decision about how the plugin is built stays an `Architecture Decision`, in `base/decisions/architecture/`. No other kind of decision is declared until one is needed.

[^adr-0028]: DEC-0003, decision 7.
[^session]: The 2026-11-04 session, "Where things go".
[^adr-0041]: SDR-0026, decisions 6 and 7.
