---
type: Knowledge Fragment
title: 2026-11-09 · An organization receives a copy of the plugin with its own version, and the installable scripts package waits
description: The owner's decision, while ticket okf-lyg.2 was being designed, that no repository needs lint outside Claude, so the installable scripts package is deferred, and that an organization receives a copy of the plugin which keeps its own version and may diverge, with the drift accepted; with the structured answers that shape ADR-0037.
tags: [fragment, decision, distribution]
status: draft
occurred_at: 2026-11-09
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "2005a969be2eb3211ccc3a7ef22fbdb2089b14ec" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-09T05:26:38Z }
---

# Record

Ticket okf-lyg.2 asked for the OKF scripts as an installable package, so that a repository runs lint at a pinned version without copying the scripts ([ADR-0034](/base/decisions/architecture/ADR-0034-organization-package.md) decision 3). The agent spiked it on a copy of the okf-standard skill: a `pyproject.toml` in the skill, the scripts unchanged, `uvx --from <dir> okf-lint` linted this repository's `knowledge/` at 0 errors, loaded the built-in profile and exited 1 on the broken fixture. The owner asked what the package solves; the agent explained that it serves a repository whose CI runs lint without Claude or the plugin.

The owner answered, on 2026-11-09 (the organization's name replaced by "[the organization]", as this repository names no organization):

> no, we are not going ahead, with this the solution is right and is good, but we do not have this problem, nor will for now, at least no in [the organization], the solution is good, and might be needed maybe in the future, but not now. the thing in [the organization] we need unforntunately to distribute the plugin so it can be installed and maintain it's own version / live with the drift risk, when we do it, since they might take it their own direction of the whole skills and plugin.

Then, to structured questions:

- okf-lyg.2: "Defer, keep the design".
- How to record the decision, which supersedes ADR-0034 decisions 2 and 3: "New ADR now".
- The epic's tickets: "Rewrite them after the ADR".
- How the organization's copy relates to okf-builder after the first delivery: "Pull when they choose": okf-builder exports a copy; the organization owns it and takes a later release only if it wants, by a pull request in its own repository; okf-builder never pushes.
- Its version: "Its own, plus the upstream base": its own semver, and a record of the okf-builder version it was taken from.
- How its repositories run lint: "From the installed plugin": the scripts of the plugin each person installs, in Claude sessions and from a pre-commit hook pointing at the installed plugin; no `okf_tooling` pin.
- What of ADR-0034 survives: "Decision 1, minus the installable package" and "Decision 4".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The spike of the installable scripts package | — | context | no concept (the design is kept in ticket okf-lyg.2) |
| No repository needs lint outside Claude; the package deferred | conflict with ADR-0034 decision 3 | applied: new ADR supersedes it | [ADR-0037](/base/decisions/architecture/ADR-0037-organization-distributed-copy.md) |
| The organization owns its copy, versions it and pulls releases when it chooses | conflict with ADR-0034 decision 2 | applied | [ADR-0037](/base/decisions/architecture/ADR-0037-organization-distributed-copy.md) |
| Lint from the installed plugin, no `okf_tooling` pin | conflict with ADR-0034 decision 3 | applied | [ADR-0037](/base/decisions/architecture/ADR-0037-organization-distributed-copy.md) |
| ADR-0034 decisions 1 (without the package) and 4 kept | update | applied: restated | [ADR-0037](/base/decisions/architecture/ADR-0037-organization-distributed-copy.md) |
| okf-lyg.2 deferred; the epic's tickets rewritten after the ADR | addition | pending: tracked as work items | tracker |
