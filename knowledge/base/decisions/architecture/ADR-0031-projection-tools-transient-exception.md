---
type: Architecture Decision
title: "ADR-0031: The projection tools are a script and a skill, run a render only on request, never ask a transient projection to be committed, and list recomputable projections for a person"
description: okf_projection.py checks projection.yaml, the dependency rule and drift by nature, and the okf-projection skill creates, refreshes and renders projections; okf_lint stays OKF-only; a rendered projection's render command runs only on an explicit flag, and what it writes is compared file by file, a transient projection's files never required to be committed; a recomputable projection is listed for a person to recompute; the skill ships in the M365 packages but not in the M365 agent.
tags: [adr, standard, projections, skills]
status: stable
adr_id: ADR-0031
decision_status: accepted
supersedes: /base/decisions/architecture/ADR-0030-projection-tools.md
superseded_by:
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: [{ by: human:jisequilla, at: 2026-11-08T14:02:25Z }, { by: human:jisequilla, at: 2026-11-14T17:01:10Z }]
sources:
  - { id: adr-0022, resource: /base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md }
  - { id: adr-0026, resource: /base/decisions/standard/SDR-0019-built-in-domain-profile.md }
  - { id: adr-0028, resource: /base/decisions/DEC-0003-where-things-go.md }
  - { id: adr-0030, resource: /base/decisions/architecture/ADR-0030-projection-tools.md }
---

# Context

[ADR-0022](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md) defines a knowledge projection, its `projection.yaml`, the dependency rule and how drift is checked for each nature, and leaves "projection tools" to own `projections/`[^adr-0022]. No such tool exists yet: nothing validates a `projection.yaml`, and the `okf-distill` step that lists the projections to refresh has nothing to read.

Three points are open in ADR-0022. Where the tools live: OKF tools skip `projections/`, so the check cannot simply be a new lint code. What the check may execute: a rendered projection is checked by running its `render` command, a command written in a file of the bundle, while a Domain Profile's validators run only on request[^adr-0026] and the bundle carries no executable code of its own[^adr-0028]. What "run the procedure again" means for a recomputable projection, whose procedure is prose over an external source that no script can run. A fourth point is packaging: the Microsoft 365 Copilot agent already declares 8 skills, the limit `make test` enforces.

The repository's owner, human:jisequilla, decided the four points in answer to structured questions on 2026-11-05, while scoping okf-t3z, and in further answers what a render writes, the level of drift and how hashes are recorded; [ADR-0030](/base/decisions/architecture/ADR-0030-projection-tools.md) recorded them[^adr-0030].

Its decision 2 makes a rendered file that is not committed drift, with no exception. A transient projection is one-shot and not committed (ADR-0022 decision 2), so under that rule every transient rendered projection in a git work tree would drift for ever; the review of the first build of the check (okf-t3z.1) found it. On 2026-11-06 the owner chose, in answer to a structured question, a new ADR that restates ADR-0030 with the exception and supersedes it.

# Decision

1. **A script and a skill.** `okf_projection.py`, in `okf-standard/scripts/` with the other scripts, checks each `projection.yaml` (the keys of ADR-0022 decision 2), the dependency rule (decision 3) and drift by nature (decision 4), honours `frozen` and reports in text and `--json`. Drift is the warning `PROJ_DRIFT`: the exit is 0 unless `--strict`, as for lint's `STALE`, because drift after a distillation asks for a refresh, not a fix. After a person approves the refresh of a composed projection, `--record-hashes <slug>` writes each ref's current `sha256` in place, leaving every other byte of `projection.yaml` as it was, and refuses, naming the ref, when a ref is not a one-line `{ path, sha256 }` map. A new skill, `okf-projection`, holds the steps to create, refresh and render a projection. `okf_lint` stays OKF-only and keeps skipping `projections/`.
2. **A render runs only on request.** Without the flag `--run-render`, the check lists each rendered projection as not checked for drift; with it, it runs the projection's `render` from the bundle root with the environment variable `OKF_PROJECTION_OUT` naming an empty temporary directory, and compares each file the command writes there with the file of the same relative path in the projection's directory; a file that differs, or, inside a git work tree, is not committed, is drift, except that a transient projection's files are never required to be committed, since a transient projection is not committed (ADR-0022 decision 2); a command that fails is an error. Rendering for real runs the same command with `OKF_PROJECTION_OUT` naming the projection's directory. An agent passes the flag only when a person asks, as for `--run-validators`. Checking a bundle never executes anything by itself.
3. **A recomputable projection is listed for a person.** The check validates its manifest and lists it as to recompute by hand; the skill describes how an agent reruns the procedure in `content.md` and proposes the difference for a person to approve.
4. **Packaging.** `okf-projection` ships in the Claude plugin, the Copilot pack, the Microsoft 365 Cowork plugin and the standalone M365 skill zips; the M365 Copilot agent keeps its 8 skills.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| The check inside `okf_lint` (`--projections`) | One tool, fewer files | An OKF tool reads what is not OKF | ADR-0022 decision 5 gives `projections/` to its own tools |
| `render` prints the content and the check compares it with `content.md` | Simplest contract | One output per projection, while a projection may render several deliverables | The owner chose an output directory |
| Always run `render` | Every rendered projection checked | Checking an untrusted bundle executes its commands | The same rule as a Domain Profile's validators |
| Leave recomputable projections out of the first version | Less to build | A declared nature with no behaviour | Listing it costs little and tells a person what to do |
| ADR-0030's rule for every lifecycle | One rule | Every transient rendered projection drifts for ever inside git | A transient projection is never committed |
| Drift as an error | CI fails until a refresh | Every distillation would break the build | Drift asks for a refresh, not a fix |
| Rewrite `projection.yaml` with a YAML dumper after a refresh | Simple | Loses comments and key order | Only the hashes change |
| Swap one of the M365 agent's skills for `okf-projection` | The agent can refresh projections | Loses a skill every bundle needs more often | The packages carry it for those who need it |

# Consequences

- Positive: a `projection.yaml` is validated before anyone relies on it; `okf-distill` has a script to ask which projections a run made stale; no projection command runs without a person's say.
- Negative / accepted debt: one more script and skill to keep in every package; a rendered projection is not checked for drift unless someone passes the flag; recomputable projections depend on a person noticing the listing.
- Follow-up actions: build okf-t3z in layers; the standard's projection section names ADR-0022 and says that only a composed projection records hashes.

# Related

* [ADR-0022: Knowledge projections](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md)
* [ADR-0026: Built-in Domain Profile](/base/decisions/standard/SDR-0019-built-in-domain-profile.md)
* [ADR-0028: Where things go](/base/decisions/DEC-0003-where-things-go.md)
* [ADR-0030: The projection tools (superseded)](/base/decisions/architecture/ADR-0030-projection-tools.md)
* [Projection](/base/domain/projection.md)

[^adr-0022]: ADR-0022, decisions 2 to 5.
[^adr-0026]: ADR-0026, validators run on request.
[^adr-0028]: ADR-0028, decision 4.
[^adr-0030]: ADR-0030, decisions 1 to 4.
