---
type: Knowledge Fragment
title: 2026-11-15 · Verification of ADR-0042 in a structured question
description: The structured question that asked the owner to verify ADR-0042, the Knowledge Viewer as a viewer setup, at the version named, and the owner's answer confirming it.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-15T17:42:41Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "4727d0d20edbbd497627565a4bece6a39a1ae252" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T17:42:41Z }
---

# Record

## ADR-0042

On branch `docs/okf-1lj-1`, before its commit. Structured question:

> Do you verify ADR-0042 (knowledge/base/decisions/architecture/ADR-0042-knowledge-viewer.md) at generated.at 2026-11-15T15:46:31Z, on branch docs/okf-1lj-1 from main 4727d0d before its commit? It decides: (1) the Knowledge Viewer is a viewer setup (ADR-0032), not a projection or a package; (2) okf_viewer.py takes a bundle root and writes, outside the bundle, index.html (from the plugin's template) and concepts.json, a snapshot naming the commit, a dirty tree and each concept's generated.at; (3) it reads the bundle as okf-lint does and refuses on SECRET_IN_BUNDLE; (4) the page is a Claude artifact for now, published by the agent, never by a script; (5) the script checks answers and writes no verified (SDR-0022); (6) the Claude plugin ships it, .agents/skills sees it through the shared source, Microsoft 365 and the Copilot pack leave it out; (7) the graph and several owners are follow-ups. Worked example: before, concepts.json rebuilt by hand each round for this repo only; after, `uv run <skills>/okf-standard/scripts/okf_viewer.py path/to/knowledge --out /tmp/viewer` → index.html + concepts.json (commit 4727d0d, 66 concepts), published as the page.

Options: "Verified" (described as: "Add verified: human:jisequilla at that generated.at, keep this question and answer as a fragment, status stable."), "Not yet" (described as: "ADR-0042 stays draft; tell me what to change."). The owner's answer: "Verified".

The decision's `generated.at` was 2026-11-15T15:46:31Z when the answer was applied.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| ADR-0042 | — | verified | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
