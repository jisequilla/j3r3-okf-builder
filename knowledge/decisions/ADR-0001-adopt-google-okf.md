---
type: Architecture Decision
title: "ADR-0001: Adopt Google's Open Knowledge Format as the basis of the standard"
description: Project knowledge is represented as an OKF bundle (markdown + YAML frontmatter) instead of a format of our own.
tags: [adr, standard]
status: stable
adr_id: ADR-0001
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

We needed a standard knowledge structure that could be reused across projects and consumed by agents. The options were a format of our own, an Obsidian vault with conventions, or adopting OKF (published by Google in June 2026; it formalizes the LLM-wiki pattern).

# Decision

We adopt OKF as the basis and define a **profile** (`knowledge/1.0`) on top of it with what OKF leaves open: directories, type vocabulary and additional required fields. See [Conformance policy](/policies/okf-conformance.md).

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Our own format | Full control | No interoperability; every consumer has to be written | OKF covers 90 % with an open standard |
| Obsidian vault | Mature tooling | Unspecified conventions; non-standard wikilinks | OKF is standard markdown and already interoperates with Knowledge Catalog |

# Consequences

- Positive: interoperable with any markdown indexer and with Google Knowledge Catalog; versionable in git; no runtime.
- Negative: dependence on how the spec evolves (v0.1→v0.2 already brought two breaking changes); mitigated in [ADR-0004](/decisions/ADR-0004-dual-support-v01-v02.md).
