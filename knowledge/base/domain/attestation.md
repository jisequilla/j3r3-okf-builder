---
type: Term
title: Attestation
description: The check, by deterministic code over the receipt of a run, that a number was produced by its sanctioned computation; okf-builder records and shape-checks an Attested Computation and runs nothing.
tags: [domain, glossary, okf, attestation]
status: stable
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-13T18:45:12Z }
verified: { by: human:jisequilla, at: 2026-11-14T17:41:38Z }
sources:
  - { id: video-review, resource: /fragments/2026-11-13-okf-v02-video-review.md, title: "Fragment: a video on the trust signals of OKF v0.2, read against this repo" }
  - { id: spec, resource: /base/references/okf-spec-google.md, title: "Open Knowledge Format (Google spec), v0.2 §10" }
---

# Definition

Attestation answers "was this number produced the way we said it must be?"[^spec]. A sanctioned computation is a concept of `type: Attested Computation`, and a concept that needs the value, such as a `Metric`, links to it. Three terms of the spec go with it[^spec]:

- **Executor**: run instructions or code that executes the computation and returns a receipt.
- **Receipt**: the evidence a run returns, such as a job id and the SQL the job executed. It is a runtime artifact, not stored in the bundle.
- **Attester**: deterministic code, with no LLM, that inspects a receipt and returns a verdict. The consumer runs it.

It is a different question from the [trust level](/base/domain/trust-level.md), which answers "can I believe this definition?" and is settled by a person, recorded in `verified`[^video-review].

# What okf-builder does with it

- The plugin records an `Attested Computation` and checks its shape: `runtime`, and a single block under `# Computation` or a `computation` path. It runs no executor and no attester[^video-review]. The spec itself executes nothing and leaves the packaging of that code outside OKF[^spec].
- `okf-ask` is a consumer, not an attester: it is an LLM that reads concepts and reports the trust signals written on them, and checks nothing against the world[^video-review].
- `okf_lint.py` is deterministic and has no LLM, but it judges a bundle's form, not a computation's receipt, so it is no attester either[^video-review].
- This repository has no data and so no computations of its own. A domain bundle holds them, in `base/computations/`, and brings the computation, the executor instructions and the attester code[^video-review].
- An `Attested Computation` is optional: it is for a number that must be produced one sanctioned way, not for every calculation[^video-review].

# Synonyms and related terms

- Not to be confused with: verification, a person's review of a concept, recorded in `verified`; and conformance, what `okf-lint` checks.

# Where it appears

* [Open Knowledge Format (Google spec)](/base/references/okf-spec-google.md)
* [OKF standard, profile knowledge/3.0](/base/references/okf-standard.md)
* [Trust level](/base/domain/trust-level.md)

[^video-review]: A video on the trust signals of OKF v0.2, read against this repo: "Is okf-ask an attester" and "Where an Attested Computation applies".
[^spec]: OKF spec v0.2, the terminology and §10.
