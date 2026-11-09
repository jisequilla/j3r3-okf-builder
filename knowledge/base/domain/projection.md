---
type: Term
title: Projection
description: Something derived from a bundle's base for a reader, kept in knowledge/projections/ with a projection.yaml; not an OKF concept.
tags: [domain, glossary, okf, projections]
status: stable
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-04T22:32:52Z }
verified: { by: human:jisequilla, at: 2026-11-09T10:55:51Z }
sources:
  - { id: adr-0022, resource: /base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md }
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
---

# Definition

Something derived from a bundle's base for a reader: a glossary, a manual, a deliverable, a briefing. It lives in `knowledge/projections/<slug>/` with a `projection.yaml` that declares its lifecycle, nature, intent and refs, and it is not an OKF concept[^adr-0022]. The per-platform outputs of this repository's skills are [platform packages](/base/domain/platform-package.md), not projections: the knowledge layer took the name, which the explored bundles use, and the exports were renamed[^bundles].

# Where it appears

* [ADR-0021: Three layers](/base/decisions/ADR-0021-three-layers-with-open-questions.md)
* [ADR-0022: Knowledge projections](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)

[^adr-0022]: ADR-0022, decisions 1, 2 and 5.
[^bundles]: What eleven real knowledge bundles teach, the name clash between the knowledge layer and the skills' exports.
