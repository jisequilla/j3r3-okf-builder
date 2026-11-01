---
type: Architecture Decision
title: "ADR-0018: A bundle has three layers, fragments, base and projections, in profile knowledge/3.0"
description: The bundle separates what was said (fragments/), what is known (base/, holding the typed directories) and what is derived for a reader (projections/); moving the typed directories under base/ is a breaking change, so the profile becomes knowledge/3.0 with a migration from 2.0.
tags: [adr, standard, profile, layers]
status: draft
adr_id: ADR-0018
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:10:00Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
  - { id: adr-0010, resource: /decisions/ADR-0010-english-canonical-profile-2.md }
  - { id: adr-0016, resource: /decisions/ADR-0016-refutation-as-a-distillation-kind.md }
---

# Context

The profile keeps a bundle's knowledge in typed directories at the root (`decisions/`, `systems/`, `runbooks/`…), next to `fragments/`, which [ADR-0016](/decisions/ADR-0016-refutation-as-a-distillation-kind.md) gave to the records of events. Eleven real bundles explored on 2026-11-01 all separate three layers instead: `fragments/`, what was said, immutable and dated; `base/`, what the team knows, in the present tense and with its sources; and `projections/`, what is derived from the base for a reader[^bundles]. KDD teaches the same three layers. The bundles also keep lists of what does not belong in the base, and a size limit per concept[^bundles].

The fragment of that review records the owner's first reading: keep the layer rule but not a `base/` directory, because the typed directories already are the knowledge layer and moving them breaks every bundle[^bundles]. Later the same day the owner reconsidered and chose `base/`: the three layers become visible in the tree, the tools get a positive rule (OKF concepts live in `base/`) instead of one by exclusion, and adopters of the explored layout and of KDD find the shape they know. Few bundles use the profile yet, so a breaking change costs least now.

# Decision

1. **A bundle has three layers**, each in its own directory under `knowledge/`:

   | Layer | Directory | What it holds | Who writes it |
   |---|---|---|---|
   | Record | `fragments/` | Events as they happened: meetings, chats, transcripts, slides. Immutable after capture | `okf-fragment` |
   | Knowledge | `base/` | The current state of what is known, as OKF concepts in the typed directories | `okf-capture`, `okf-distill`, `okf-review` |
   | Derivation | `projections/` | What is derived from the base for a reader; not OKF concepts ([ADR-0019](/decisions/ADR-0019-knowledge-projections.md)) | projection tools |

2. **The typed directories move under `base/`**: `base/architecture/`, `base/decisions/`, `base/domain/`, `base/systems/`, `base/apis/`, `base/data/`, `base/metrics/`, `base/computations/`, `base/runbooks/`, `base/playbooks/`, `base/policies/`, `base/references/`, and any directory a bundle adds. Bundle paths follow (`/base/decisions/ADR-0001-....md`).
3. **The root keeps only what is about the bundle as a whole**: `index.md` (with `okf_version` and `okf_profile`), `log.md`, `project.md` and `conflict-log.md`, plus the three layer directories.
4. **Writing in `base/`**: concepts state the current state in the present tense, with their sources; dated history goes to `log.md` and to the fragments, not into the prose. A concept with several topics, or longer than about 300 lines, is split.
5. **What stays in fragments and does not reach `base/`**: logistics, action items, tone, commercial terms, and proposals nobody has validated; a proposal is distilled only as a proposal (an ADR with `decision_status: proposed`, or an open question).
6. **The profile becomes `knowledge/3.0`.** `okf_lint` validates 2.0 and 3.0 bundles by the `okf_profile` the root declares, and `okf-init` writes 3.0. `okf-migrate` moves a 2.0 bundle to 3.0: it moves the typed directories under `base/`, rewrites the bundle-path links and `sources` that point into them, and logs a **Migration** entry. The OKF version (0.1 or 0.2) is independent of the profile and does not change.
7. **OKF tools read `fragments/` and `base/`, and skip `projections/`.**

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep the typed directories at the root; the knowledge layer is everything except `fragments/` and `projections/` | No migration | The boundary works by exclusion and is not visible; differs from KDD and from the bundles in use | The owner chose a visible layer while the profile has few users |
| Make `base/` optional, both shapes valid | No forced migration | Two shapes for every tool to handle, and links that depend on which one a bundle uses | One shape per profile version is simpler for tools and people |
| A central registry for fragment state, as most explored bundles keep | One file to read | It is where most of their drift was, and the latest of them moved state back into frontmatter[^bundles] | Fragment state stays in each fragment's frontmatter |

# Consequences

- Positive: the three layers are visible in every bundle; the tools know where concepts are; the shape matches KDD and the explored bundles.
- Negative / accepted debt: every 2.0 bundle needs `okf-migrate`, this repository's included; links into a bundle from outside it break when it migrates; `okf-init`, the templates, `okf_index.py`, `okf_lint.py`, `okf_migrate.py`, the skills and both copies of the standard change.
- Follow-up actions: the standard (§2 layout, §4 usual directories, §5 reserved files, §9 versions) and its compatibility matrix; the 2.0 → 3.0 migration in `okf_migrate.py` with its tests; 3.0 in `okf_init.py`, `okf_lint.py` and `okf_index.py`; the skills' paths; migrate this repository and `examples/knowledge`; tell the KDD bundle's session.

# Related

* [ADR-0010: English canonical, profile knowledge/2.0](/decisions/ADR-0010-english-canonical-profile-2.md)
* [ADR-0016: Distillation adds refutation](/decisions/ADR-0016-refutation-as-a-distillation-kind.md)
* [ADR-0019: Knowledge projections](/decisions/ADR-0019-knowledge-projections.md)

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
