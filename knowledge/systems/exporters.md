---
type: System
title: Projection exporters
description: tools/export_copilot.py and tools/export_m365.py generate the skill projections for other repos and for Microsoft 365 Copilot.
resource: /tools
tags: [system, exporters, m365, copilot]
status: draft
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T14:00:00Z }
---

# Responsibility

| Exporter | Output | For |
|---|---|---|
| export_copilot.py | `dist/copilot/.github/skills`, `.github/agents/okf.agent.md`, `AGENTS.okf.md` | Vendoring skills into another repo (Copilot, Claude, Gemini) |
| export_m365.py | `dist/m365/okf-builder-m365.zip` (manifest v1.28) and `dist/m365/skills/*.zip` | M365 Cowork plugin and per-skill upload in Copilot Studio / Agent Builder |

# Applicable rules

- They replace the `<skills>/` convention with the concrete path of the target.
- M365: they copy into each skill the scripts and templates it needs (`NEEDS` table; `okf-init` gets only the templates `okf_init.py` renders), keep only `references/` in okf-standard, whose templates live in `okf-capture`, to respect the 20-companion limit, point a skill to `okf-migrate` when it does not ship `okf_migrate.py`, and add `license`/`metadata` and an environment note. `okf-capture` sits at the limit: a new template needs room made first.
- The M365 manifest uses a stable GUID (uuid5 of the repo URL).

# Operation

* [Export and deliver projections](/runbooks/export-projections.md)
* Decision: [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md)
