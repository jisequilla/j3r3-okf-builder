---
type: Architecture Decision
title: "ADR-0007: Single source of skills and per-platform projections"
description: Skills live only once in plugin/okf-builder/skills; each platform receives a projection (symlink or generated package).
tags: [adr, architecture]
status: stable
adr_id: ADR-0007
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

The same operational knowledge must work in Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot. All of them adopt the Agent Skills standard (`SKILL.md`), but each discovers or packages it differently and has its own limits (M365: ≤20 companion files per skill, self-contained skills). Keeping per-platform copies would diverge.

# Decision

- **Single source**: `plugin/okf-builder/skills/`. Scripts in `okf-standard/scripts/`, templates in `okf-standard/templates/`.
- Skills use no vendor's variables; they use the `<skills>/...` convention (the skill's parent).
- **Link projections**: `.claude/skills` and `.agents/skills` → source (Claude Code; Copilot and Gemini).
- **Generated projections**: `make plugin` (Cowork), `make m365` (M365, self-contained per skill), `make copilot` (vendorable pack). Output in `dist/`, not versioned.
- See [architecture view](/architecture/single-source-projections.md).

# Alternatives considered

| Alternative | Cons | Reason rejected |
|---|---|---|
| Per-platform copies in the repo | They diverge; 5× maintenance | It is the problem we want to avoid |
| Claude plugin only + third-party converters (`atk import openplugin`, `wiqd`) | They neither rewrite paths nor distribute scripts | Insufficient for M365 |

# Consequences

- Positive: one change, every platform; `make check-links` and `make all` verify it.
- Negative: symlinks require `core.symlinks` on Windows; in that case use `make copilot` and copy.
