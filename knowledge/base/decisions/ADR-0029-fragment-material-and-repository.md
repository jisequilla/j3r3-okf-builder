---
type: Architecture Decision
title: "ADR-0029: A fragment records its frozen material by SHA-256 and may freeze a repository at a commit, through a map field type"
description: A Knowledge Fragment may list the files its record was taken from, each with its SHA-256, and the repository it was taken from at a full commit; the standard gains a one-level map field type to declare both, lint hashes material found in the bundle and reports a changed file as an error, and okf-fragment adds the meeting discipline.
tags: [adr, standard, profile, fragments]
status: draft
adr_id: ADR-0029
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-04T18:33:13Z }
sources:
  - { id: review, resource: /fragments/2026-11-02-migration-tool-okf-review.md, title: "Fragment: what a long-running OKF implementation teaches" }
  - { id: adr-0024, resource: /base/decisions/ADR-0024-fragment-capture-field-backfill.md }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: standard, resource: standard/OKF-STANDARD.md, title: "OKF standard §4, §4.1 and §7" }
---

# Context

The review of a migration tool that has used OKF for months, and of the design meetings around it, found that a fragment there is a folder with its material frozen and its SHA-256 recorded, and that a repository frozen at a commit is a fragment too[^review]. Decision 4 of that review sent both, with the meeting discipline of `okf-fragment` (gaps and attribution in the transcript, the raw transcript never altered, non-professional content left out before freezing, confirmation with someone who was there), to the audit and the skills "without an ADR".

A record that cannot change after capture ([ADR-0024](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)) is only as good as its source: when the record was taken from a file, nothing showed that the file still holds what was captured[^adr-0024]. Recording the digest of that file needs a field whose value is a structure, `{ path, sha256 }`, and the field types of [ADR-0026](/base/decisions/ADR-0026-built-in-domain-profile.md) are scalars and lists of scalars only[^adr-0026].

The repository's owner, human:jisequilla, decided both points in answers to structured questions, as ADR-0027 records its own decision: on 2026-11-03 to write a short ADR for the fragment material and the repository at a commit, in place of the "without an ADR" of decision 4, superseding nothing; and on 2026-11-04 to add a `map` field type to the standard, recorded in this ADR with the two fields, and to make a changed material file an error.

# Decision

1. **A `map` field type** (standard §4.1): `{ type: map, keys: { ... } }`, and `{ type: list, of: map, keys: { ... } }` for a list of them. Each key is a field definition of a scalar type (any type but `list` and `map`: one level deep) with its own `required` (`true` or `false`), `values` for an enum and a `note`, and no level or code of its own. A value that is not a map, a missing required key and a key of another type are breaches of the field, at its level and under its code; a key the declaration does not name is not reported. A lower layer never changes an inherited map field's `keys` (`PROFILE_REDEFINED`); extending a map across layers is later work. This refines ADR-0026's field types and supersedes nothing.
2. **`material`** (optional, Knowledge Fragment): a list of `{ path, sha256 }`, each file the record was taken from. `path` is a bundle path (`/...`) or relative to the bundle root, never to the fragment's directory; a file at the repository root is named with `../` and stays outside the bundle. `sha256` is the 64-hex digest of the file as kept, the redacted one when `okf-fragment` redacted it. An entry that breaks this form is `BAD_MATERIAL`, a warning of the built-in Domain Profile.
3. **Lint hashes material found in the bundle**: a file whose SHA-256 differs from the recorded one is `FRAGMENT_MATERIAL_CHANGED`, an **error** of the OKF profile, because a changed source breaks the record's immutability (ADR-0024). An absent file, a path that leaves the bundle or one inside a nested bundle is a notice and is never read: material may live outside the repository. A file `.okfignore` excludes is still hashed, since it is not judged as a concept.
4. **`repository`** (optional, Knowledge Fragment): `{ url, commit }`, the repository the record was taken from, at its full 40-hex commit. A non-map value, a missing or non-text `url`, or a `commit` that is missing, short or not hex is `BAD_REPOSITORY`, a warning. Lint never fetches it.
5. **A repository at a commit is a field, not a fragment kind.** The review asked for "a fragment kind for a repository at a commit"[^review]. A fragment stays the record of an event, a reading of the repository included; the repository is that record's origin, as `origin` names a meeting, so it is a field of Knowledge Fragment and every local type that extends it, and no new type splits the record layer.
6. **`okf-fragment`** computes `material` when the person hands it files and writes `repository` with the commit read from git, and adds the meeting discipline: gaps and unclear passages marked in the transcript and attributed to who said what, the raw transcript never altered after capture, non-professional content left out before freezing (and said so in the record), and the record confirmed with someone who was there before it is distilled.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| A `map` field type, `material` and `repository` as fields, a changed file an error | One generic check for any structured field; the record's source is checked; no new type | A new field type in the standard; a value YAML reads as a number must be quoted | Chosen |
| Refinements without an ADR, as decision 4 of the review said | No ADR to write | A new field type, a new error and a new rule for the record's immutability would land with no recorded reason | The owner chose a short ADR |
| A new fragment type for a repository at a commit | Matches the review's wording | Splits the record layer by origin; every skill that reads fragments learns a second type | A repository is the origin of a record, not a kind of event |
| The hex checks as declarable constraints of a map key (a `pattern`) | Bundles could declare their own formats | Widens §4.1 beyond the `map` type the owner decided | Kept in lint for these two fields |
| A changed material file as a warning | Never fails lint without `--strict` | A changed source passes CI unnoticed | The owner made it an error |

# Consequences

- Positive: a fragment taken from a file can show that its source was not altered; a repository reading names exactly the commit it read; any bundle can declare a structured field with the `map` type.
- Negative / accepted debt: lint checks only material kept in the bundle; material outside it (slides, recordings at `/sources`) is a notice, not checked. The hex forms of `sha256` and `commit` are code for these two fields, not something a profile declares.
- Follow-up actions: standard §4, §4.1 and §7 (both copies), the built-in profile, the fragment template, `okf_profile.py`, `okf_lint.py`, the `okf-fragment` and `okf-lint` skills, and one fragment in examples/knowledge that records its material.

# Related

* [ADR-0024: A fragment's record is immutable](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)
* [ADR-0026: The standard's own types are a built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [ADR-0027: The owner of an operational concept is a string](/base/decisions/ADR-0027-owner-is-a-string-actor-stays-the-spec.md)

[^review]: Fragment of 2026-11-02, "What the design meetings add" and the owner's decision 4.
[^adr-0024]: ADR-0024: after capture the record never changes.
[^adr-0026]: ADR-0026, decision 3: the field types.
