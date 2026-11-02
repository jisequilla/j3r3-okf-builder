---
type: Domain Profile
title: Built-in Domain Profile of knowledge/3.0
description: The types of the OKF standard's §4 with their usual directory, their extra fields and the code and level lint reports for each breach; the first layer of every bundle's Domain Profile.
tags: [profile, taxonomy, built-in]
status: draft
types:
  Project:
    directory: /
    description: Project overview, exactly one per bundle (project.md)
  Architecture View:
    directory: /base/architecture/
    description: Context, containers, components, deployment, principles
  Architecture Decision:
    directory: /base/decisions/
    description: An architecture decision record
    fields:
      adr_id: { type: string, note: "ADR-NNNN, the prefix of the file name" }
      decision_status: { type: enum, values: [proposed, accepted, superseded, rejected] }
      supersedes: { type: path, note: The decision this one replaces }
      superseded_by: { type: path, note: The decision that replaces this one }
  Term:
    directory: /base/domain/
    description: A business term
  Glossary:
    directory: /base/domain/
    description: The aggregated glossary
  System:
    directory: /base/systems/
    description: Service, module, job, deployable component
    fields:
      owner: { type: actor, note: Who answers for the system }
      repo: { type: string, note: The repository that holds its code }
      runtime: { type: string, note: Where and how it runs }
  API:
    directory: /base/apis/
    description: A contract; resource points to the OpenAPI, Proto or AsyncAPI document
    fields:
      owner: { type: actor, note: Who answers for the contract }
  Dataset:
    directory: /base/data/
    description: A data asset
  Table:
    directory: /base/data/
    description: A data asset
    fields:
      owner: { type: actor, note: Who answers for the table }
  Metric:
    directory: /base/metrics/
    description: A business definition that links to its Attested Computation
    fields:
      owner: { type: actor, note: Who answers for the definition }
  Attested Computation:
    directory: /base/computations/
    description: The sanctioned computation of a value, a type the OKF spec names (§10)
    fields:
      runtime: { type: string, note: "Required by the OKF spec (§10.2); lint checks it with the spec-level checks, as AC_NO_RUNTIME" }
  Runbook:
    directory: /base/runbooks/
    description: "Operational procedure: trigger, diagnosis, steps, rollback, escalation"
    fields:
      owner: { type: actor, note: Who answers for the procedure }
  Playbook:
    directory: /base/playbooks/
    description: Team or business procedure
    fields:
      owner: { type: actor, note: Who answers for the procedure }
  Policy:
    directory: /base/policies/
    description: A rule or standard
    fields:
      owner: { type: actor, note: Who answers for the rule }
  Reference:
    directory: /base/references/
    description: Mirrored external material or execution instructions
  Knowledge Fragment:
    directory: /fragments/
    description: The record of an event as it happened, named YYYY-MM-DD-slug.md
    fields:
      occurred_at: { type: date_or_datetime, level: warn, code: BAD_ISO, required: { level: warn, code: FRAGMENT_NO_FIELD }, note: "When it happened: YYYY-MM-DD or ISO 8601 with an offset" }
      origin: { type: string, level: warn, required: { level: warn, code: FRAGMENT_NO_FIELD }, note: Where it happened }
      participants: { type: list, of: actor, level: warn, code: BAD_ACTOR, required: { level: warn, code: FRAGMENT_NO_FIELD }, note: "Who took part, as actors" }
      distillation_status: { type: enum, values: [pending, distilled, conflict], code: BAD_DISTILLATION_STATUS, required: { level: warn, code: FRAGMENT_NO_FIELD } }
  Open Question:
    directory: /base/questions/
    description: What the team does not know yet, named <kebab-slug>.md
    fields:
      owner: { type: actor, level: warn, code: BAD_ACTOR, required: { level: warn, code: QUESTION_NO_FIELD }, note: Who answers for the question }
      question_status: { type: enum, values: [open, answered, dropped], code: BAD_QUESTION_STATUS, required: { level: warn, code: QUESTION_NO_FIELD } }
      asked_in: { type: path, level: warn, required: { level: warn, code: QUESTION_NO_FIELD }, note: "The fragment where it arose, /fragments/<file>" }
      blocks: { type: list, of: path, level: warn, note: The concepts it holds up }
      answered_by: { type: path, level: warn, note: The concept that answers it }
      review_on: { type: date_or_datetime, level: warn, code: BAD_ISO, note: The date to look at it again }
  Conflict Log:
    directory: /
    description: The bundle's conflict register, conflict-log.md, zero or one per bundle
  Domain Profile: {}
  Log: {}
rules:
  - { name: answered-question-names-its-answer, when: { type: Open Question, question_status: answered }, require: [answered_by], level: warn, code: QUESTION_NO_ANSWER }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T21:00:00Z }
sources:
  - { id: types, resource: references/OKF-STANDARD.md, title: "OKF standard §4: Profile type vocabulary" }
  - { id: domain-profile, resource: references/OKF-STANDARD.md, title: "OKF standard §4.1: Domain Profile" }
  - { id: frontmatter, resource: references/OKF-STANDARD.md, title: "OKF standard §3.1: Frontmatter" }
  - { id: conformance, resource: references/OKF-STANDARD.md, title: "OKF standard §7: Conformance" }
  - { id: spec-computation, resource: references/OKF-SPEC-v0.2.md, title: "OKF spec v0.2 §10.2: Contract fields of an Attested Computation" }
---

# What this profile holds

The types of the standard's type vocabulary, each with its usual directory and the extra fields the standard gives it[^types]. It is the first layer of every bundle's Domain Profile: a bundle without `base/profile.md` is checked against it alone, and a bundle's own profile only adds to it[^domain-profile]. Its content changes only with the standard.

`directory` is the usual directory of a type, written as a bundle path. It is a default, not a rule, so this profile declares no `families`. `Domain Profile` and `Log` are declared by name only: the keys of a Domain Profile are nested maps that no field type describes, and lint checks them itself against §4.1; a `Log` is `log.md` with optional frontmatter.

# What lint reports from it

A requirement that declares a `code` is reported under that code at its declared level, so the per-field checks of a Knowledge Fragment and an Open Question keep the codes and levels they had in code[^domain-profile]: `FRAGMENT_NO_FIELD` and `QUESTION_NO_FIELD` (warnings), `BAD_DISTILLATION_STATUS` and `BAD_QUESTION_STATUS` (errors), `BAD_ACTOR` and `BAD_ISO` (warnings). These are reported in every bundle. A blank value (empty text, list or map) counts as missing.

A field without a code is checked in a bundle that has a `base/profile.md`, like every item of that bundle's own profile: at its declared level, `error` when absent, under the generic code of §4.1 (`PROFILE_ENUM` for a value outside an enum, `PROFILE_FIELD_TYPE` for a value of another type), with `built-in` as its source[^domain-profile]. A bundle without a `base/profile.md` gets no finding from them. `okf-lint --profiles` lists every field with its type and note.

The keys every concept may carry stay with the spec-level checks, in code, because they apply to every type, an undeclared one included[^frontmatter]: `generated` (`PROFILE_NO_GENERATED` in a 0.2 bundle, `PROFILE_NO_TIMESTAMP` for `timestamp` in a 0.1 one, `BAD_GENERATED`), `verified` (`BAD_VERIFIED`), `status` (`BAD_STATUS`), `stale_after` (`STALE`), `sources` (`BAD_SOURCES`), and the `BAD_ACTOR` and `BAD_ISO` checks of their actors and timestamps.

So do the checks across concepts or over a body (ADR-0026, decision 6)[^domain-profile]: at most one Conflict Log per bundle, the layer rule of a 3.0 bundle, an open question past its `review_on` (`QUESTION_REVIEW_DUE`), the single fence of an Attested Computation, and the structure of `index.md` and `log.md`. They apply to a local type through the standard type it extends.

# Types

## Project, Conflict Log

At the root of the bundle: `project.md`, exactly one, and `conflict-log.md`, zero or one, created with the first conflict[^types]. That there is one of each is checked across concepts, in code.

## Architecture View, Term, Glossary, Dataset, Reference

No extra fields: the common keys of §3.1 and the body headings of their templates are enough[^types]. `Term` and `Glossary` share a directory.

## API, Table, Metric, Runbook, Playbook, Policy

- `owner`: who answers for the contract, the table, the definition, the procedure or the rule[^types]. It is an actor (§3.1). `Table` shares its directory with `Dataset`.

## Architecture Decision

- `adr_id`, `supersedes`, `superseded_by`: the identity of the decision and the decisions it replaces or that replace it[^types].
- `decision_status`: `proposed`, `accepted`, `superseded` or `rejected`[^types].

## System

- `owner`, `repo`, `runtime`: who answers for it, where its code lives, where it runs[^types]. `owner` is an actor (§3.1).

## Attested Computation

- `runtime`: required by the OKF spec for this type, whatever the profile[^spec-computation], so lint reports its absence with the spec-level checks (`AC_NO_RUNTIME`), `--no-profile` included. The single block under `# Computation` is a body check and stays in code.

## Knowledge Fragment

- `occurred_at`, `origin`, `participants`, `distillation_status`: each one missing is a warning, `FRAGMENT_NO_FIELD`[^types].
- `occurred_at` is `YYYY-MM-DD` or ISO 8601 with an offset; another form is `BAD_ISO`, a warning.
- `participants` is a list of actors; an entry that does not follow the actor convention is `BAD_ACTOR`, a warning. A single value is read as a one-item list.
- `distillation_status` is `pending`, `distilled` or `conflict`; another value is `BAD_DISTILLATION_STATUS`, an error, because the distillation workflow reads it[^conformance].

## Open Question

- `owner`, `question_status`, `asked_in`: each one missing is a warning, `QUESTION_NO_FIELD`[^types].
- `owner` is an actor; another form is `BAD_ACTOR`, a warning.
- `question_status` is `open`, `answered` or `dropped`; another value is `BAD_QUESTION_STATUS`, an error[^conformance].
- `blocks`, `answered_by`, `review_on`: optional. `review_on` is `YYYY-MM-DD` or ISO 8601 with an offset; another form is `BAD_ISO`, a warning.
- Rule `answered-question-names-its-answer`: an answered question names the concept that answers it in `answered_by`; without it, `QUESTION_NO_ANSWER`, a warning[^types].

## Domain Profile, Log

Declared by name only, as above[^domain-profile].
