---
type: Runbook
title: Publish a plugin version
description: Steps to release a new version of okf-builder on every platform.
tags: [runbook, release]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T03:59:10Z }
---

# Trigger

A change in skills, scripts, templates or the standard that must reach users.

# Steps

1. Update `version` in `plugin/okf-builder/.claude-plugin/plugin.json` and in `.claude-plugin/marketplace.json` (semver).
2. If a decision changed: a new ADR with `okf-capture`; record it in `knowledge/log.md`.
3. `make all` → `test`, `plugin`, `copilot`, `m365`. It must end in `OK`.
4. `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
5. `make lint` (own knowledge/ and example at 0 errors).
6. Commit + tag `v<version>` + push. Claude Code: `/plugin marketplace update`.
7. GitHub Release for the tag, with notes on what changed for users and the built files attached: `okf-builder.plugin`, `dist/okf-copilot-pack.zip`, `dist/m365/okf-builder-m365.zip`.
8. Deliver projections: see [Export projections](/runbooks/export-projections.md).

# Rollback

Delete the GitHub Release and the tag, and republish the previous version; users' bundles do not change with the plugin version.
