---
type: Runbook
title: Publish a plugin version
description: Steps to release a new version of okf-builder on every platform.
tags: [runbook, release]
status: stable
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: { by: human:jisequilla, at: 2026-11-09T10:56:05Z }
---

# Trigger

release-please's open release pull request holds changes that must reach users ([DEC-0005](/base/decisions/DEC-0005-release-please.md)).

# Steps

1. Each change reaches main as a squash-merged pull request whose title follows Conventional Commits ([DEC-0005](/base/decisions/DEC-0005-release-please.md) decisions 2 to 4): `feat:` or `fix:` for a change to the plugin (`plugin/okf-builder/`), text included; `docs:`, `test:`, `build:`, `ci:` or `chore:` for anything else, which never raises the version; a pull request that changes `.claude-plugin/marketplace.json` raises its top-level `version` by hand; `!` and a `BREAKING CHANGE:` footer when a bundle that passed lint would fail it; CI has run `just test` and `just lint` on it and checked the title. If a decision changed, it carries a new ADR (`okf-capture`) recorded in `knowledge/log.md`.
2. release-please keeps the release pull request `chore(main): release <version>` up to date on every push to main: `version` in `plugin/okf-builder/.claude-plugin/plugin.json` and the version's section in `plugin/okf-builder/CHANGELOG.md`, from the pull requests that touched the plugin. To set a version the titles would not give, merge a commit with the footer `Release-As: <version>`.
3. Read the release pull request: the version is the one intended, and each changelog line says what changed for users. To fix a line, add to the body of the merged pull request it came from a block `BEGIN_COMMIT_OVERRIDE` … `END_COMMIT_OVERRIDE` holding the corrected title; release-please rewrites the line on its next run. An edit made by hand on the release pull request's branch is overwritten by the next push to main.
4. On the release pull request's branch: `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
5. The owner merges the release pull request. release-please tags `v<version>` and creates the GitHub release with the changelog section as notes; the `release-please` workflow checks out the tag, runs `just all` and attaches `okf-builder.plugin`, `dist/okf-copilot-pack.zip`, `dist/m365/okf-builder-m365.zip` and `dist/m365/okf-knowledge-architect-m365.zip`.
6. Check that the release carries the four files (`gh release view v<version>`). Claude Code: `/plugin marketplace update`.
7. Record the release in `knowledge/log.md` in one line naming the version, in a `docs:` pull request.
8. Deliver platform packages: see [Export platform packages](/base/runbooks/export-projections.md).

# Rollback

Delete the GitHub Release and the tag, and republish the previous version; users' bundles do not change with the plugin version.
