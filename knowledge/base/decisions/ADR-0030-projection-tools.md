---
type: Architecture Decision
title: "ADR-0030: The projection tools are a script and a skill, run a render only on request, and list recomputable projections for a person"
description: okf_projection.py checks projection.yaml, the dependency rule and drift by nature, and the okf-projection skill creates, refreshes and renders projections; okf_lint stays OKF-only; a rendered projection's render command runs only on an explicit flag; a recomputable projection is listed for a person to recompute; the skill ships in the M365 packages but not in the M365 agent.
tags: [adr, standard, projections, skills]
status: draft
adr_id: ADR-0030
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-05T22:35:12Z }
sources:
  - { id: adr-0022, resource: /base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md }
---

# Context

[ADR-0022](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md) defines a knowledge projection, its `projection.yaml`, the dependency rule and how drift is checked for each nature, and leaves "projection tools" to own `projections/`[^adr-0022]. No such tool exists yet: nothing validates a `projection.yaml`, and the `okf-distill` step that lists the projections to refresh has nothing to read.

Three points are open in ADR-0022. Where the tools live: OKF tools skip `projections/`, so the check cannot simply be a new lint code. What the check may execute: a rendered projection is checked by running its `render` command, a command written in a file of the bundle, while a Domain Profile's validators run only on request[^adr-0026] and the bundle carries no executable code of its own[^adr-0028]. What "run the procedure again" means for a recomputable projection, whose procedure is prose over an external source that no script can run. A fourth point is packaging: the Microsoft 365 Copilot agent already declares 8 skills, the limit `make test` enforces.

The repository's owner, human:jisequilla, decided the four points in answer to structured questions on 2026-11-05, while scoping okf-t3z.

# Decision

1. **A script and a skill.** `okf_projection.py`, in `okf-standard/scripts/` with the other scripts, checks each `projection.yaml` (the keys of ADR-0022 decision 2), the dependency rule (decision 3) and drift by nature (decision 4), honours `frozen`, reports in text and `--json`, and records the refs' hashes of a composed projection only when asked after a person approved a refresh. A new skill, `okf-projection`, holds the steps to create, refresh and render a projection. `okf_lint` stays OKF-only and keeps skipping `projections/`.
2. **A render runs only on request.** Without the flag `--run-render`, the check lists each rendered projection as not checked for drift; with it, it runs the projection's `render` and compares the result with what is committed. An agent passes the flag only when a person asks, as for `--run-validators`. Checking a bundle never executes anything by itself.
3. **A recomputable projection is listed for a person.** The check validates its manifest and lists it as to recompute by hand; the skill describes how an agent reruns the procedure in `content.md` and proposes the difference for a person to approve.
4. **Packaging.** `okf-projection` ships in the Claude plugin, the Copilot pack, the Microsoft 365 Cowork plugin and the standalone M365 skill zips; the M365 Copilot agent keeps its 8 skills.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| The check inside `okf_lint` (`--projections`) | One tool, fewer files | An OKF tool reads what is not OKF | ADR-0022 decision 5 gives `projections/` to its own tools |
| Always run `render` | Every rendered projection checked | Checking an untrusted bundle executes its commands | The same rule as a Domain Profile's validators |
| Leave recomputable projections out of the first version | Less to build | A declared nature with no behaviour | Listing it costs little and tells a person what to do |
| Swap one of the M365 agent's skills for `okf-projection` | The agent can refresh projections | Loses a skill every bundle needs more often | The packages carry it for those who need it |

# Consequences

- Positive: a `projection.yaml` is validated before anyone relies on it; `okf-distill` has a script to ask which projections a run made stale; no projection command runs without a person's say.
- Negative / accepted debt: one more script and skill to keep in every package; a rendered projection is not checked for drift unless someone passes the flag; recomputable projections depend on a person noticing the listing.
- Follow-up actions: build okf-t3z in layers; the standard's projection section names ADR-0022 and says that only a composed projection records hashes.

# Related

* [ADR-0022: Knowledge projections](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)
* [ADR-0026: Built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [ADR-0028: Where things go](/base/decisions/ADR-0028-where-things-go.md)
* [Projection](/base/domain/projection.md)

[^adr-0022]: ADR-0022, decisions 2 to 5.
[^adr-0026]: ADR-0026, validators run on request.
[^adr-0028]: ADR-0028, decision 4.
