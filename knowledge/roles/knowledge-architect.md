---
type: Role Profile
title: Knowledge architect
description: How okf-builder serves the KDD knowledge architect role, which the KDD bundle defines; this concept fixes the skills its agent carries, what it hands to a person and its fragment contract with the functional architect.
tags: [role, knowledge-architect, agents, kdd]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T20:35:00Z }
sources:
  - { id: kdd-role, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/roles/arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect role profile v1.1, human-verified" }
  - { id: kdd-agent, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/agents/agente-arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect agent definition (draft)" }
  - { id: kdd-agent-v2, resource: "https://github.com/jisequilla/kdd-knowledge/blob/e4afa95/knowledge/agents/agente-arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect agent definition, five distillation kinds" }
  - { id: kdd-af, resource: "https://github.com/jisequilla/kdd-knowledge/blob/81828dd/knowledge/roles/arquitecto-funcional-ti.md", title: "KDD bundle: functional architect role profile" }
  - { id: adr-0005, resource: /decisions/ADR-0005-required-generated-human-verified.md }
  - { id: adr-0017, resource: /decisions/ADR-0017-agent-skills-per-platform.md }
  - { id: adr-0016, resource: /decisions/ADR-0016-refutation-as-a-distillation-kind.md }
---

# Definition

The knowledge architect turns an organisation's knowledge into a versioned, traceable bundle that people and agents can query. It is the main role of Knowledge Driven Development (KDD). Its mission, scope, responsibilities (AC-R1 to AC-R9), decision limits and interactions are defined in the KDD bundle, where a person has verified them[^kdd-role]. This bundle does not restate them.

The role can be held by a person or by an agent, and the tasks are the same either way. A person always approves the final result[^kdd-role]. This concept covers only what okf-builder decides: the tools the role uses, the agent that [ADR-0017](/decisions/ADR-0017-agent-skills-per-platform.md) projects from this profile, and the contract with the functional architect.

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

The Claude agent preloads all 10 plugin skills[^adr-0017]. The Microsoft 365 agent carries at most 8, the M365 limit, chosen in `tools/m365-agent.json`: `okf-init`, `okf-capture`, `okf-fragment`, `okf-distill`, `okf-review`, `okf-index`, `okf-lint` and `okf-ask`. `okf-standard` and `okf-migrate` stay out of it[^adr-0016].

The agent's source is `plugin/okf-builder/agents/knowledge-architect.md`, written from this profile and from the KDD agent definition as of kdd-knowledge commit `e4afa95`[^kdd-agent-v2]. At that commit the KDD role is v1.2 (distillation in five kinds) and awaits a person's re-verification. `make m365` generates the M365 declarative agent from the same file ([Exporters](/systems/exporters.md)).

In the M365 agent package none of its 8 skills reads `okf-standard`'s references or templates: each carries the scripts and templates it uses. Only `okf-capture` names the `okf-standard` type table when it classifies a concept, and its templates cover the same types.

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

- The KDD agent draft lists `okf-migrate` among its tools[^kdd-agent]. Here only the Claude agent carries it.
- The KDD bundle keeps its own agent definition next to the okf-builder agent. The two are kept in step by hand: a change to one is carried to the other in the same piece of work.

# Not verified

- Whether Microsoft 365 accepts the generated agent package and runs its skills; no tenant with Copilot has been available to test it.

# Related

* [ADR-0017: The Claude agent preloads every skill it needs; the M365 agent takes a configured subset](/decisions/ADR-0017-agent-skills-per-platform.md)
* [ADR-0016: Distillation adds refutation](/decisions/ADR-0016-refutation-as-a-distillation-kind.md)
* [Actor](/domain/actor.md)

[^kdd-role]: KDD bundle, knowledge architect role profile v1.1.
[^kdd-agent]: KDD bundle, knowledge architect agent definition.
[^kdd-agent-v2]: KDD bundle, knowledge architect agent definition with the five distillation kinds.
[^kdd-af]: KDD bundle, functional architect role profile.
[^adr-0005]: ADR-0005, `generated` required and `verified` only by people.
[^adr-0017]: ADR-0017, decisions 3 and 5.
[^adr-0016]: ADR-0016, decisions 5, 6, 9 and 10.
