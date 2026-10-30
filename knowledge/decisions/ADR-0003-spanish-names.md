---
type: Architecture Decision
title: "ADR-0003: Profile directories and types in Spanish"
description: Profile directories and type values are in Spanish, except references/ and Attested Computation, which the spec fixes.
tags: [adr, structure]
status: deprecated
adr_id: ADR-0003
decision_status: superseded
superseded_by: /decisions/ADR-0010-english-canonical-profile-2.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

The standard's user and their teams work in Spanish. The OKF spec neither imposes directory names nor registers types.

# Decision

Directories and types in Spanish:

| Item | Spanish names |
|---|---|
| Directories | `decisiones/`, `runbooks/`, `politicas/`… |
| Types | `Decisión de Arquitectura`, `Métrica`… |

Only the names that the spec fixes or uses as a convention stay in English: `references/` (§6.3) and `type: Attested Computation` (§10).

# Consequences

- Positive: readability for the teams; indexes and descriptions are consistent in one language.
- Negative: the spec's examples and Google's bundles use English; consumers must tolerate unknown types (the spec requires it, §11).
