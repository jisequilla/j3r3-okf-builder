---
type: Term
title: Projection
description: Something derived from a bundle's base for a reader, kept in knowledge/projections/ with a projection.yaml; not an OKF concept.
tags: [domain, glossary, okf, projections]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:15:00Z }
sources:
  - { id: adr-0019, resource: /decisions/ADR-0019-knowledge-projections.md }
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
---

# Definition

Something derived from a bundle's base for a reader: a glossary, a manual, a deliverable, a briefing. It lives in `knowledge/projections/<slug>/` with a `projection.yaml` that declares its lifecycle, nature, intent and refs, and it is not an OKF concept[^adr-0019]. The per-platform outputs of this repository's skills are [platform packages](/domain/platform-package.md), not projections.

# Where it appears

* [ADR-0018: Three layers](/decisions/ADR-0018-three-layers-fragments-base-projections.md)
* [ADR-0019: Knowledge projections](/decisions/ADR-0019-knowledge-projections.md)

[^adr-0019]: ADR-0019, decisions 1, 2 and 5.
