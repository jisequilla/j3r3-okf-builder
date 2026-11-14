---
type: Term
title: Projection
description: Something derived from a bundle's base for a reader, kept in knowledge/projections/ with a projection.yaml; not an OKF concept.
tags: [domain, glossary, okf, projections]
status: stable
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:55:51Z }, { by: human:jisequilla, at: 2026-11-14T17:31:13Z }]
sources:
  - { id: adr-0022, resource: /base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md }
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
---

# Definition

Something derived from a bundle's base for a reader: a glossary, a manual, a deliverable, a briefing. It lives in `knowledge/projections/<slug>/` with a `projection.yaml` that declares its lifecycle, nature, intent and refs, and it is not an OKF concept[^adr-0022]. The per-platform outputs of this repository's skills are [platform packages](/base/domain/platform-package.md), not projections: the knowledge layer took the name, which the explored bundles use, and the exports were renamed[^bundles].

# Where it appears

* [SDR-0014: Three layers](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md)
* [SDR-0015: Knowledge projections](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md)

[^adr-0022]: SDR-0015, decisions 1, 2 and 5.
[^bundles]: What eleven real knowledge bundles teach, the name clash between the knowledge layer and the skills' exports.
