---
type: Architecture Decision
title: "ADR-0028: Where things go: four homes, workspace tooling as a projection of knowledge, and a Doctrine for how we build"
description: The repo's files belong to one of four homes (product, product build, knowledge, workspace); the knowledge bundle carries no executable code except a Domain Profile's validators; workspace tooling such as an agent workflow is a projection of a knowledge concept and names it; how the repo builds with agents becomes a Doctrine, a local type refined as practice teaches.
tags: [adr, repo, agents, doctrine, layout]
status: draft
adr_id: ADR-0028
decision_status: proposed
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-04T07:21:40Z }
sources:
  - { id: adr-0007, resource: /base/decisions/ADR-0007-single-source-and-projections.md }
  - { id: adr-0009, resource: /base/decisions/ADR-0009-build-in-layers-and-tickets.md }
  - { id: adr-0013, resource: /base/decisions/ADR-0013-agent-projections.md }
  - { id: adr-0022, resource: /base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: runbook, resource: /base/runbooks/build-in-layers.md }
  - { id: readme, resource: README.md, title: "README, repository map (templates/ row)" }
---

# Context

The repo builds its multi-layer changes with agents, as [ADR-0009](/base/decisions/ADR-0009-build-in-layers-and-tickets.md) decided and the runbook [Build a change in layers](/base/runbooks/build-in-layers.md) describes[^adr-0009][^runbook]. The tool that runs it, an agent workflow (pre-flight, a builder in a worktree with a draft PR, two fresh-context reviewers, at most two fix rounds), lives only in one session's private folder: it is not versioned, and another session or person cannot find or run it.

Running ticket A2 of the knowledge audit taught practice that is written nowhere: the ticket files kept in a session's scratch folder were lost and rebuilt from the tracker; four pre-flights stopped on data the ticket had not looked at (each proposed check was first measured against the repo's own bundles there); a builder died when the machine slept and its work was saved and resumed; a review found a secret echoed by another check and labelled it a fix, though the ticket's bar made it blocking. ADRs cannot hold such practice, because history is never edited; a Policy holds rules without the evidence that taught them.

Asking where the workflow script should live showed that the repo has no rule for where anything goes. Its files fall into kinds that are not named: `tools/` holds the platform package exporters, a root `templates/` copy duplicates the source templates and is kept identical by a `diff` in `make test` (the README calls it "canonical copy"[^readme], while [ADR-0007](/base/decisions/ADR-0007-single-source-and-projections.md) makes `plugin/okf-builder/skills/` the single source[^adr-0007]), and the standard exists as two identical copies.

# Decision

1. **Every file belongs to one of four homes**, named by what it is, not by who uses it:

   | Home | What it holds | Where |
   |---|---|---|
   | Product | what is shipped: skills, scripts, templates, the standard | `plugin/`, `standard/` |
   | Product build | what turns the source into platform packages and checks it | `Makefile`, `tools/`, `tests/` |
   | Knowledge | what the project knows and how it works, readable on any platform | `knowledge/` |
   | Workspace | how agents operate in this repo, specific to a tool | `.claude/`, `.agents/`, `.beads/`, the context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) |

2. **The knowledge bundle carries no executable code**, except the validators a Domain Profile declares ([ADR-0026](/base/decisions/ADR-0026-built-in-domain-profile.md)), which the standard runs only on request[^adr-0026]. The bundle travels and is projected to platforms that cannot run code, and `okf_lint` judges it: it does not carry its own judge.
3. **Workspace tooling is a projection of a knowledge concept**, as the knowledge-architect agent is a per-platform projection of its role ([ADR-0013](/base/decisions/ADR-0013-agent-projections.md))[^adr-0013]: an agent workflow names in its header the runbook or doctrine it carries out, and that concept names the workflow in `resource`. A change to how the repo works starts in the concept; the projection follows. Projections drift by nature ([ADR-0022](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)), so the link both ways is what lets a review find the drift[^adr-0022].
4. **Agent workflows live in `.claude/workflows/`**, versioned, where Claude Code finds saved workflows by name. The first is the layer-ticket workflow that runs the runbook.
5. **How the repo builds with agents becomes a Doctrine**: a local type declared in a new `knowledge/base/profile.md`, in `base/doctrine/`. A doctrine is a set of principles, each with its statement, why it holds and the evidence that taught it (a link to an ADR, a fragment or a PR). It is edited in place as practice teaches (a new `generated.at` and a `log.md` entry); new practice enters as a fragment and is distilled with `okf-distill`, approved by a person. A principle that becomes a decision is an ADR; the doctrine then links it.

# Doctrine outline (first doctrine: building with agents)

Each principle below lists the evidence it would cite; the build writes them as the doctrine's body.

1. **The main session judges and does not implement.** Evidence: ADR-0009.
2. **The ticket's text lives in the tracker**, never only in a session's scratch folder. Evidence: the 2026-11-04 session, where the scratch ticket files were gone and were rebuilt from the beads.
3. **Measure a proposed check against the repo's own data before the ticket is written.** Run the idea over `knowledge/`, `examples/` and the fixtures and count what it would report. Evidence: A2's four pre-flights, each stopped by data (a secret pattern matching 176 ADR file names, citations of pending fragments, a verification older than a migration).
4. **An agent's report is a claim.** Verify on a fresh checkout of the pushed ref (a clone of the local repo takes the local branch), and compare lint's `--json` between main and the PR. Evidence: the A1 verification.
5. **Classify findings against the ticket's bar, not the reviewer's label.** A security property the bar names is blocking even when reported as a fix. Evidence: PR #57, a secret echoed by `BAD_STATUS` and `BROKEN_LINK`.
6. **Unattended runs need the machine awake, and interrupted work is kept.** Keep the machine awake for the length of the run; save an interrupted builder's work as a local WIP commit, resume the workflow from that branch so the cached pre-flight is reused, and squash before the PR. Evidence: the A2 build killed by sleep on 2026-11-04.
7. **An owner's decision is asked as a structured question, with a recommendation**, and settles only what it names; what the builder can settle from the context is written into the ticket instead. Evidence: A2's three rounds of owner questions.

Harness-specific practice (for example, the exact phrase that lets a merge through an agent's permission classifier) is workspace knowledge, not doctrine: it stays with the tool.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Four homes; workspace tooling projects knowledge; Doctrine as a local type | One rule for every new file; the practice is versioned, refinable and cited; dogfoods Domain Profiles on the repo's own bundle | One more type and a `base/profile.md` to keep | Proposed |
| Add the lessons to the runbook and the agents policy | No new type | Procedure, rules and lessons mix; a principle loses its evidence; the runbook grows into a diary | The practice changes faster than the procedure |
| Keep the workflow script in the knowledge bundle | One place for the practice and its tool | Executable code in a bundle that travels to platforms that cannot run it; the bundle would carry its own tooling | Decision 2 |
| Keep the workflow in the session folder | Nothing to maintain | Unversioned; invisible to other sessions and people | The problem this ADR answers |

# Consequences

- Positive: a new file has one obvious home; the practice of building with agents is versioned, cited and refined through the product's own fragment → distill loop; the workflow is runnable by name from any session in the repo.
- Negative / accepted debt: the doctrine and the workflow can drift; only the links both ways and a review catch it. `base/profile.md` adds a Domain Profile to a bundle that had none.
- Open points for the owner, settled while building:
  - the root `templates/` copy and the standard's second copy: keep them as checked copies, generate them with `make`, or drop the root `templates/` (it predates ADR-0007 and the README calls it canonical);
  - whether `tools/` keeps its name or becomes `build/`;
  - whether the agents policy (`AGENTS.md`'s source) becomes part of the doctrine or stays a Policy the doctrine links.
- Follow-up actions: `knowledge/base/profile.md` with the Doctrine type; a fragment of the 2026-11-04 session and the first doctrine distilled from it; the workflow in `.claude/workflows/` with links both ways; the runbook naming the workflow and the doctrine; the README map naming the four homes.

# Related

* [ADR-0007: Single source of skills and per-platform projections](/base/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0009: Build multi-stage changes in layers and delegated tickets](/base/decisions/ADR-0009-build-in-layers-and-tickets.md)
* [ADR-0013: One knowledge-architect agent for Claude and Microsoft 365 Copilot](/base/decisions/ADR-0013-agent-projections.md)
* [ADR-0022: Knowledge projections are declared in a projection.yaml, and their drift is checked according to their nature](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)
* [ADR-0026: The standard's own types are a built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [Build a change in layers](/base/runbooks/build-in-layers.md)

[^adr-0007]: ADR-0007, decision "Single source".
[^adr-0009]: ADR-0009, decision 3.
[^adr-0013]: ADR-0013, one role projected to each platform's agent format.
[^adr-0022]: ADR-0022, drift checked according to the projection's nature.
[^adr-0026]: ADR-0026, validators run only with `--run-validators`.
[^runbook]: Build a change in layers, step 5.
[^readme]: README.md, the `templates/` row of the repository map.
