---
type: Architecture Decision
title: "ADR-0002: One bundle per repository in knowledge/"
description: Each repo carries its knowledge in knowledge/, co-located with the code, not in a central repo.
tags: [adr, structure]
status: stable
adr_id: ADR-0002
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

Options: a bundle inside each repo, a central knowledge repo, or a hybrid with an aggregated index.

# Decision

**Inside each repo**, in `knowledge/` at the root. The bundle travels with the code, is reviewed in the same PRs, and agents working on the repo find it without configuration.

# Consequences

- Positive: unified versioning and review; trivial discovery (`knowledge/index.md`).
- Negative: there is no cross-project view out of the box; if one is needed, a consumer can aggregate several bundles (out of scope, see [project](/project.md)).
