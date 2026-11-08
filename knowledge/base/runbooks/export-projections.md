---
type: Runbook
title: Export and deliver platform packages
description: How to generate and deliver the Cowork plugin, the M365 package and the pack for other repos.
tags: [runbook, release, m365, copilot]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:34:38Z }
---

# Steps

| Target | Command | Delivery |
|---|---|---|
| Claude Code (this repo) | nothing: `.claude/skills` is a symlink | `just check-links` |
| Claude Code (others) | `/plugin marketplace add <owner>/j3r3-okf-builder` | the repo's marketplace |
| Claude Cowork | `just plugin` → `okf-builder.plugin` | drag into a Claude chat (not through iMessage: it treats it as an unknown zip) |
| GitHub Copilot / Gemini (this repo) | nothing: `.agents/skills` is a symlink | — |
| GitHub Copilot / Gemini (other repos) | `just copilot` → `dist/copilot/` | copy into the root of the target repo |
| M365 Copilot Cowork | `just m365` → `dist/m365/okf-builder-m365.zip` | admin center → Manage apps → Upload custom app; or `atk install --file-path … --scope Personal` |
| Copilot Studio / Agent Builder | `just m365` → `dist/m365/skills/*.zip` | Build → Skills → Upload a skill |

# Checks

- `grep -rn '<skills>' dist/` must find only the definition of the convention in okf-standard.
- M365: no skill exceeds 20 companions; the exporter fails if one does, and `just test` runs it.

# Knowledge in M365

M365 Copilot reads `knowledge/` from its one source ([ADR-0014](/base/decisions/ADR-0014-knowledge-repository-storage.md)):

- Git source: connect the repository with the GitHub Cloud Knowledge connector, which indexes `.md` and keeps GitHub permissions. M365 only reads; changes go back by PR.
- SharePoint source: add the library as a knowledge source of the agent. `.md` is not a documented SharePoint knowledge file type, so check in the tenant that Copilot answers from it.

# Rollback

A platform package is built from a tagged version, so a bad one is replaced by the previous version's, never patched by hand:

- Claude Code: `/plugin marketplace update` after the bad release is fixed, or install the previous version from the marketplace.
- Claude Cowork: drag in the previous `okf-builder.plugin`, attached to the previous GitHub Release.
- M365 Copilot Cowork: upload the previous `okf-builder-m365.zip` (previous GitHub Release) in the admin center, or remove the custom app.
- Copilot Studio / Agent Builder: upload the previous skill zip, rebuilt with `just m365` from the previous tag.
- Pack copied into another repo: revert that repo's commit that copied it.
