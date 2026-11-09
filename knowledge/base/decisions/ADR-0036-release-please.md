---
type: Architecture Decision
title: "ADR-0036: Releases are proposed by release-please from squash-merged pull requests with Conventional Commit titles, and a workflow attaches the platform packages"
description: Pull requests are squash-merged and their titles follow Conventional Commits, so each change reaches main as one commit release-please reads; release-please keeps a release pull request open that bumps the version in plugin.json and marketplace.json and writes CHANGELOG.md; merging it tags and publishes the release, and a GitHub Actions workflow builds the platform packages with just all and attaches them; a CI workflow runs just test and just lint on every pull request and checks its title; knowledge/log.md keeps the knowledge history and records each release in one line.
tags: [adr, release, build, ci]
status: draft
adr_id: ADR-0036
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-09T00:24:32Z }
sources:
  - { id: adr-0007, resource: /base/decisions/ADR-0007-single-source-and-projections.md }
  - { id: adr-0034, resource: /base/decisions/ADR-0034-organization-package.md }
  - { id: adr-0035, resource: /base/decisions/ADR-0035-just-build-runner.md }
  - { id: runbook, resource: /base/runbooks/release-version.md }
---

# Context

A release followed [Publish a plugin version](/base/runbooks/release-version.md) by hand: the version edited in two files, the build run, a tag pushed, a GitHub release written and four built files attached[^runbook]. Each step is a chance to skip one, and the release notes were written from memory. The organization package of ADR-0034 needs versions people can pin, arriving at a steady cadence[^adr-0034].

release-please reads the commit history since the last release and proposes the next one. It reads Conventional Commits (`feat:`, `fix:`, `!` for a breaking change). This repository's commits were prose sentences and its pull requests were merged with merge commits, so release-please would have found nothing to release. The repository had no CI.

The owner, human:jisequilla, proposed release-please on 2026-11-07 and decided its shape in answer to structured questions on 2026-11-09 (okf-lyg.12).

# Decision

1. **Pull requests are squash-merged, and their titles follow Conventional Commits.** The title becomes the one commit on main: a type (`feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`), an optional scope, `!` for a breaking change, then the prose sentence this repository writes. Commits on a branch need no convention. A CI check rejects a pull request whose title does not follow it.
2. **release-please proposes each release.** On every push to main it keeps a release pull request open, which bumps `version` in `plugin/okf-builder/.claude-plugin/plugin.json` and in `.claude-plugin/marketplace.json` and adds the version's section to `CHANGELOG.md`, from the titles of the pull requests merged since the last tag. Before 1.0, `feat` bumps the minor version, `fix` the patch, and a breaking change the minor version. A commit footer `Release-As: <version>` sets the version when the titles would not.
3. **Merging the release pull request publishes the release.** release-please tags `v<version>` and creates the GitHub release with that section as its notes; a workflow then checks out the tag, runs `just all` (ADR-0035)[^adr-0035] and attaches `okf-builder.plugin`, `dist/okf-copilot-pack.zip`, `dist/m365/okf-builder-m365.zip` and `dist/m365/okf-knowledge-architect-m365.zip`. Merging it is the owner's act, like any release.
4. **CI runs the checks on every pull request.** A workflow runs `just test` and `just lint` on each pull request and each push to main.
5. **`CHANGELOG.md` holds the release notes; `knowledge/log.md` holds the knowledge history.** The changelog says what changed for users, version by version. The log keeps recording each change to the bundle, and records each release in one line that names the version.
6. **Actions are pinned to a commit.** Each workflow names every third-party action by its full commit SHA, with the release tag as a comment.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep releasing by hand | Nothing new | Steps skipped, notes from memory | It is what the automation removes |
| Conventional Commits on every commit, merge commits kept | No change to merging | Every working commit must follow the convention | Only the title reaching main needs it |
| No CHANGELOG, notes on the GitHub release only | One history in the repo | Notes are not in the repository a reader clones | Users read release notes, the log records knowledge |
| Attach the assets by hand after release-please tags | No CI | The step most often skipped stays manual | A workflow builds from the tag, the same every time |

# Consequences

- Positive: a release is one merge; the version files, tag, notes and assets cannot disagree; every pull request is checked before merge.
- Negative / accepted debt: titles must follow the convention; a release pull request opened with the workflow's own token does not trigger the CI workflow, so its checks are the ones that ran on the pull requests it collects; the repository settings must allow only squash merges with the pull request title as the commit, and allow GitHub Actions to create pull requests.
- Follow-up actions: the release runbook follows this decision; `AGENTS.md` and [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md) state the title rule; the `okf-layer-ticket` workflow titles its pull requests by it.

# Related

* [ADR-0035: The product build runs with just](/base/decisions/ADR-0035-just-build-runner.md)
* [ADR-0034: The organization package](/base/decisions/ADR-0034-organization-package.md)
* [Publish a plugin version](/base/runbooks/release-version.md)

[^runbook]: Publish a plugin version, Steps, as it stood before this decision.
[^adr-0034]: ADR-0034, decision 3.
[^adr-0035]: ADR-0035, decision 1.
