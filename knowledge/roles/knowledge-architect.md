---
type: Role Profile
title: Knowledge architect
description: How okf-builder serves the KDD knowledge architect role, which the KDD bundle defines; this concept fixes the skills its agent carries, what it hands to a person and its fragment contract with the functional architect.
tags: [role, knowledge-architect, agents, kdd]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T12:00:00Z }
sources:
  - { id: kdd-role, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/roles/arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect role profile v1.1, human-verified" }
  - { id: kdd-agent, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/agents/agente-arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect agent definition (draft)" }
  - { id: kdd-af, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/roles/arquitecto-funcional-ti.md", title: "KDD bundle: functional architect role profile" }
  - { id: adr-0005, resource: /decisions/ADR-0005-required-generated-human-verified.md }
  - { id: adr-0013, resource: /decisions/ADR-0013-agent-projections.md }
  - { id: adr-0016, resource: /decisions/ADR-0016-refutation-as-a-distillation-kind.md }
---

# Definition

The knowledge architect turns an organisation's knowledge into a versioned, traceable bundle that people and agents can query. It is the main role of Knowledge Driven Development (KDD). Its mission, scope, responsibilities (AC-R1 to AC-R9), decision limits and interactions are defined in the KDD bundle, where a person has verified them[^kdd-role]. This bundle does not restate them.

The role can be held by a person or by an agent, and the tasks are the same either way. A person always approves the final result[^kdd-role]. This concept covers only what okf-builder decides: the tools the role uses, the agent that [ADR-0013](/decisions/ADR-0013-agent-projections.md) projects from this profile, and the contract with the functional architect.

# Responsibilities and the skills that serve them

| KDD responsibility[^kdd-role] | okf-builder skill | State |
|---|---|---|
| AC-R1 Knowledge architecture (structure, types, conventions) | `okf-init`, `okf-standard` | exists |
| AC-R2 Receiving fragments | `okf-fragment` | to build ([ADR-0016](/decisions/ADR-0016-refutation-as-a-distillation-kind.md)) |
| AC-R3 Distillation | `okf-distill`; `okf-capture` for new concepts | `okf-distill` to build |
| AC-R4 Double check and lifecycle (log, conflict register, deprecation) | `okf-review`, `okf-lint` | `okf-review` to build |
| AC-R5 Indexing, search and answers | `okf-index`, `okf-ask` | exists |
| AC-R6 Graph visualisation | none yet | outside the plugin's skills |
| AC-R7 Federation by domain | none; the split rule is [ADR-0014](/decisions/ADR-0014-knowledge-repository-storage.md) | — |
| AC-R8 Knowledge health metrics | `okf-lint --json` | metrics not built |
| AC-R9 Enablement and training | none | — |

# The agent's skills

The agent carries 8 skills, the Microsoft 365 limit[^adr-0013]: `okf-init`, `okf-capture`, `okf-fragment`, `okf-distill`, `okf-review`, `okf-index`, `okf-lint` and `okf-ask`. `okf-migrate` stays out of the M365 agent[^adr-0016]. Claude users still have it as a plugin skill.

# What it decides and what it hands to a person

| Decides alone | Proposes; a person decides |
|---|---|
| Folders, file names, links, indexes and log entries | Each distillation change set, before it is applied[^adr-0016] |
| Classifying each item of a fragment (addition, confirmation, update, refutation, conflict)[^adr-0016] | The resolution of every conflict in the [conflict log](/conflict-log.md) |
| When `okf-lint` must run, and fixing what it reports | Domains and bounded contexts, restructurings and deprecations[^kdd-role] |
| | Moving a concept to human-verified: it never writes `verified: human:`[^adr-0005] |

Approving a change set does not verify a concept. Verification is a separate act by a person[^adr-0016].

# Working with the functional architect

The functional architect asks the business questions and captures functional knowledge. The knowledge architect does not capture business knowledge[^kdd-role][^kdd-af]. The interface between them is the fragment format of [ADR-0016](/decisions/ADR-0016-refutation-as-a-distillation-kind.md): a `Knowledge Fragment` in `fragments/` with `occurred_at`, `origin`, `participants` and `distillation_status: pending`.

| Direction | What is handed over |
|---|---|
| Functional → knowledge architect | Fragments with the event recorded as it happened |
| Knowledge → functional architect | Knowledge gaps, clarification questions and open conflicts that need the business |

The two agents live in separate repositories. As long as both keep to the fragment format, either can change without touching the other.

# Differences with the KDD bundle

- The KDD agent draft lists `okf-migrate` among its tools[^kdd-agent]. Here it is a Claude-only skill.
- The KDD bundle keeps its own agent definition next to the okf-builder agent. The two are kept in step by hand: a change to one is carried to the other in the same piece of work.

# Not verified

- Whether the M365 agent's skills can still read `okf-standard`'s references and templates when `okf-standard` itself is not among its 8 `agent_skills`.

# Related

* [ADR-0013: One knowledge-architect agent for Claude and Microsoft 365 Copilot](/decisions/ADR-0013-agent-projections.md)
* [ADR-0016: Distillation adds refutation](/decisions/ADR-0016-refutation-as-a-distillation-kind.md)
* [Actor](/domain/actor.md)

[^kdd-role]: KDD bundle, knowledge architect role profile v1.1.
[^kdd-agent]: KDD bundle, knowledge architect agent definition.
[^kdd-af]: KDD bundle, functional architect role profile.
[^adr-0005]: ADR-0005, `generated` required and `verified` only by people.
[^adr-0013]: ADR-0013, decision 3.
[^adr-0016]: ADR-0016, decisions 5, 6, 9 and 10.
