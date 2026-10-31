---
type: Runbook
title: Export and deliver projections
description: How to generate and deliver the Cowork plugin, the M365 package and the pack for other repos.
tags: [runbook, release, m365, copilot]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Steps

| Target | Command | Delivery |
|---|---|---|
| Claude Code (this repo) | nothing: `.claude/skills` is a symlink | `make check-links` |
| Claude Code (others) | `/plugin marketplace add <owner>/j3r3-okf-builder` | the repo's marketplace |
| Claude Cowork | `make plugin` → `okf-builder.plugin` | drag into a Claude chat (not through iMessage: it treats it as an unknown zip) |
| GitHub Copilot / Gemini (this repo) | nothing: `.agents/skills` is a symlink | — |
| GitHub Copilot / Gemini (other repos) | `make copilot` → `dist/copilot/` | copy into the root of the target repo |
| M365 Copilot Cowork | `make m365` → `dist/m365/okf-builder-m365.zip` | admin center → Manage apps → Upload custom app; or `atk install --file-path … --scope Personal` |
| Copilot Studio / Agent Builder | `make m365` → `dist/m365/skills/*.zip` | Build → Skills → Upload a skill |

# Checks

- `grep -rn '<skills>' dist/` must find only the definition of the convention in okf-standard.
- M365: no skill exceeds 20 companions (the exporter fails if it happens).

# Knowledge in M365

M365 Copilot reads `knowledge/` from its one source ([ADR-0014](/decisions/ADR-0014-knowledge-repository-storage.md)):

- Git source: connect the repository with the GitHub Cloud Knowledge connector, which indexes `.md` and keeps GitHub permissions. M365 only reads; changes go back by PR.
- SharePoint source: add the library as a knowledge source of the agent. `.md` is not a documented SharePoint knowledge file type, so check in the tenant that Copilot answers from it.
