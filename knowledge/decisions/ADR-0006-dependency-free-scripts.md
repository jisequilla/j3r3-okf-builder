---
type: Architecture Decision
title: "ADR-0006: Python scripts without external dependencies"
description: The tools (init, lint, index, migrate) are Python ≥ 3.9 without pip; PyYAML is used only if present.
tags: [adr, tooling]
status: stable
adr_id: ADR-0006
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

The tools must run in any agent's sandbox (Claude, Copilot, Gemini, M365) and in CI, where there is not always network access or permission to install packages.

# Decision

No dependencies. `okf_common.py` includes a reduced YAML parser for OKF frontmatter and uses PyYAML if it exists. The scripts are copied as they are into `tools/okf/` of other repos for CI.

# Consequences

- Positive: runnable in any sandbox; copyable.
- Negative: the mini-parser does not cover full YAML (anchors, multi-line `|`); it is enough for OKF frontmatter, and it is tested against Google's real bundles.
