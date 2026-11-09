---
type: Architecture Decision
title: "ADR-0035: The product build runs with just, and its checks are named steps of a build script"
description: A justfile replaces the Makefile as the product build's runner; every check of just test is a named step of build/checks.py, a PEP 723 script that runs the scripts as a person would and writes to one temporary directory per run; the root copies are written by build/copies.py; earlier ADRs keep naming make as the history of the decisions they record.
tags: [adr, build, repo]
status: draft
adr_id: ADR-0035
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:33:29Z }
sources:
  - { id: adr-0011, resource: /base/decisions/ADR-0011-uv-pep723-scripts.md }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md }
  - { id: runbook, resource: /base/runbooks/build-in-layers.md }
---

# Context

The product build (ADR-0028 decision 1) ran with a Makefile[^adr-0028]. Its `test` target had grown to about forty shell lines, most of them `python3 -c` one-liners asserting a fact, and the gates read lint's last line through `| tail -1`. macOS ships GNU Make 3.81, which ignores `.SHELLFLAGS`, so a failure inside a pipe passed until the shell flags moved into `SHELL` itself; the [build-in-layers runbook](/base/runbooks/build-in-layers.md) carried that trap as a warning[^runbook]. The steps wrote to fixed `/tmp/okf-*` paths, so two runs at once collided. Two of the repositories reviewed on 2026-11-07 already run their build with a justfile.

The owner, human:jisequilla, proposed the switch on 2026-11-07 and decided its shape in answer to structured questions on 2026-11-08 (okf-cby).

# Decision

1. **just is the product build's runner.** A `justfile` at the root replaces the `Makefile`, which is deleted: `just test`, `just lint`, `just copies`, `just plugin`, `just copilot`, `just m365`, `just obsidian`, `just all`, `just secrets` and `just check-links` do what the make targets of the same names did. A recipe a later decision names, such as ADR-0034's organization package, is a just recipe.
2. **Every check is a named step of `build/checks.py`.** The script carries its dependencies as PEP 723 metadata (ADR-0011)[^adr-0011] and runs the scripts as a person would, through `uv run`, judging each by its exit code and its JSON output rather than by text read through a pipe. `just test` runs every step in order; `just test <step>` runs only the steps named; `build/checks.py --list` names them and what each checks. A new cross-script check is a new step, not a shell line.
3. **One temporary directory per run.** The steps write to a directory created for the run and removed at its end, so two runs at once no longer collide on it; `dist/`, which the exporters own, is still shared.
4. **The root copies are written by `build/copies.py`**, which `just copies` runs and the `copies` step compares with the committed `standard/` and `templates/` (ADR-0028 decision 2)[^adr-0028].
5. **History keeps naming make.** ADRs, fragments and log entries written before this decision keep their `make` commands as the record of what was decided and run then; the concepts that describe how the repo works today (runbooks, policies, systems, the architecture view) and the context files name the just recipes.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep make, move the one-liners into a script | Nothing new to install | Tabs, `.PHONY`, the 3.81 shell-flag trap and no arguments remain | The runner was half of the problem |
| just, with the one-liners ported unchanged into a shell recipe | Smallest diff | The checks stay unreadable and pipe-judged | Readable checks were the point |
| A Makefile shim calling just | `make test` keeps working | Two runners to keep in step | Contributors install just once |
| A Python task runner (nox, invoke) | Python only | A runner in every check's path; nothing the steps need | just runs a one-line recipe per task, and checks.py holds the logic |

# Consequences

- Positive: each check is named, readable and runnable alone; a failing step says which check failed and shows the command's output; no gate depends on shell pipe flags; runs at once no longer collide in `/tmp`; the build runs wherever just and uv run, Windows included.
- Negative / accepted debt: contributors install just; `dist/` is still shared by runs at once.
- Follow-up actions: the runbooks, policies, systems, architecture view, `AGENTS.md`, the READMEs and the `okf-layer-ticket` workflow name the just recipes.

# Related

* [ADR-0028: Where things go](/base/decisions/ADR-0028-where-things-go.md)
* [ADR-0011: Scripts run with uv and declare PyYAML inline (PEP 723)](/base/decisions/ADR-0011-uv-pep723-scripts.md)
* [Build a change in layers](/base/runbooks/build-in-layers.md)
* [Publish a plugin version](/base/runbooks/release-version.md)

[^adr-0028]: ADR-0028, decisions 1 and 2.
[^adr-0011]: ADR-0011, Decision.
[^runbook]: Build a change in layers, Warnings.
