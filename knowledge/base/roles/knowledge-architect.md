---
type: Role Profile
title: Knowledge architect
description: How okf-builder serves the KDD knowledge architect role, which the KDD bundle defines; this concept fixes the skills its agent carries, what it hands to a person and its fragment contract with the functional architect.
tags: [role, knowledge-architect, agents, kdd]
status: stable
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: { by: human:jisequilla, at: 2026-11-09T10:56:23Z }
sources:
  - { id: kdd-role, resource: "https://github.com/jisequilla/kdd-knowledge/blob/929515c/knowledge/base/roles/arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect role profile v1.3, human-verified" }
  - { id: kdd-agent, resource: "https://github.com/jisequilla/kdd-knowledge/blob/929515c/knowledge/base/agents/agente-arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect agent definition, ten skills" }
  - { id: kdd-agent-v2, resource: "https://github.com/jisequilla/kdd-knowledge/blob/e4afa95/knowledge/agents/agente-arquitecto-del-conocimiento.md", title: "KDD bundle: knowledge architect agent definition, five distillation kinds" }
  - { id: kdd-af, resource: "https://github.com/jisequilla/kdd-knowledge/blob/929515c/knowledge/base/roles/arquitecto-funcional-ti.md", title: "KDD bundle: functional architect role profile" }
  - { id: adr-0025, resource: /base/decisions/standard/SDR-0018-verification-recorded-by-question.md }
  - { id: adr-0033, resource: /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md }
  - { id: adr-0017, resource: /base/decisions/architecture/ADR-0017-agent-skills-per-platform.md }
  - { id: adr-0024, resource: /base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md }
  - { id: adr-0031, resource: /base/decisions/architecture/ADR-0031-projection-tools-transient-exception.md }
---

# Definition

The knowledge architect turns an organisation's knowledge into a versioned, traceable bundle that people and agents can query. It is the main role of Knowledge Driven Development (KDD). Its mission, scope, responsibilities (AC-R1 to AC-R9), decision limits and interactions are defined in the KDD bundle, where a person has verified them[^kdd-role]. This bundle does not restate them.

The role can be held by a person or by an agent, and the tasks are the same either way. A person always approves the final result[^kdd-role]. This concept covers only what okf-builder decides: the tools the role uses, the agent that [ADR-0017](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md) projects from this profile, and the contract with the functional architect.

# Responsibilities and the skills that serve them

| KDD responsibility[^kdd-role] | okf-builder skill | State |
|---|---|---|
| AC-R1 Knowledge architecture (structure, types, conventions) | `okf-init`, `okf-standard` | exists |
| AC-R2 Receiving fragments | `okf-fragment` | exists; it also backfills missing capture fields ([SDR-0017](/base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md)) |
| AC-R3 Distillation | `okf-distill`; `okf-capture` for new concepts | exists |
| AC-R4 Double check and lifecycle (log, conflict register, deprecation) | `okf-review`, `okf-lint` | exists |
| AC-R5 Indexing, search and answers | `okf-index`, `okf-ask` | exists |
| AC-R6 Graph visualisation | none yet | outside the plugin's skills |
| AC-R7 Federation by domain | none; the split rule is [SDR-0008](/base/decisions/standard/SDR-0008-knowledge-repository-storage.md) | — |
| AC-R8 Knowledge health metrics | `okf-lint --json` | metrics not built |
| AC-R9 Enablement and training | none | — |

# The agent's skills

The Claude agent preloads all 11 plugin skills[^adr-0017]. The Microsoft 365 agent carries at most 8, the M365 limit, chosen in `build/m365-agent.json`: `okf-init`, `okf-capture`, `okf-fragment`, `okf-distill`, `okf-review`, `okf-index`, `okf-lint` and `okf-ask`. `okf-standard` and `okf-migrate` stay out of it[^adr-0017], and so does `okf-projection`, which ships in the M365 packages but not in the agent[^adr-0031]. The agent routes projection requests to `okf-projection` and never answers from `projections/`.

The agent's source is `plugin/okf-builder/agents/knowledge-architect.md`, written from this profile and from the KDD agent definition as of kdd-knowledge commit `e4afa95`[^kdd-agent-v2]. At that commit the KDD role is v1.2 (distillation in five kinds); a person verified v1.3 at kdd-knowledge commit `5a6412d`, and its agent under SDR-0018 at `929515c`[^kdd-role]. `just m365` generates the M365 declarative agent from the same file ([Exporters](/base/systems/exporters.md)).

In the M365 agent package none of its 8 skills reads `okf-standard`'s references or templates: each carries the scripts and templates it uses. Only `okf-capture` names the `okf-standard` type table when it classifies a concept, and its templates cover the same types.

# What it decides and what it hands to a person

| Decides alone | Proposes; a person decides |
|---|---|
| Folders, file names, links, indexes and log entries | Each distillation change set, before it is applied[^adr-0024] |
| Classifying each item of a fragment (addition, confirmation, update, refutation, conflict)[^adr-0024] | The resolution of every conflict in the [conflict log](/conflict-log.md) |
| When `okf-lint` must run, and fixing what it reports | Domains and bounded contexts, restructurings and deprecations[^kdd-role] |
| | Moving a concept to human-verified: it writes `verified: human:` only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and its version[^adr-0033] |

Approving a change set does not verify a concept. Verification is a separate act by a person[^adr-0024].

# Working with the functional architect

The functional architect asks the business questions and captures functional knowledge. The knowledge architect does not capture business knowledge[^kdd-role][^kdd-af]. The interface between them is the fragment format of [SDR-0017](/base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md): a `Knowledge Fragment` in `fragments/` with `occurred_at`, `origin`, `participants` and `distillation_status: pending`.

| Direction | What is handed over |
|---|---|
| Functional → knowledge architect | Fragments with the event recorded as it happened |
| Knowledge → functional architect | Knowledge gaps, clarification questions and open conflicts that need the business |

The two agents live in separate repositories. As long as both keep to the fragment format, either can change without touching the other.

# Differences with the KDD bundle

- The KDD agent definition lists 10 skills[^kdd-agent], every plugin skill except `okf-projection`; the Claude agent preloads all 11. The Microsoft 365 agent carries 8, without `okf-standard`, `okf-migrate` and `okf-projection`[^adr-0017][^adr-0031].
- The KDD bundle's validation policy also accepts a person's written chat confirmation when the changes apply that person's answers literally, as a local exception to [SDR-0018](/base/decisions/standard/SDR-0018-verification-recorded-by-question.md) decided by its owner[^kdd-agent]. The okf-builder agent never applies it.
- The KDD bundle keeps its own agent definition next to the okf-builder agent. The two are kept in step by hand: a change to one is carried to the other in the same piece of work.

# Not verified

- Whether Microsoft 365 accepts the generated agent package and runs its skills; no tenant with Copilot has been available to test it.

# Related

* [ADR-0017: The Claude agent preloads every skill it needs; the M365 agent takes a configured subset](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md)
* [SDR-0017: Fragment record immutable, capture fields backfilled from it](/base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md)
* [Actor](/base/domain/actor.md)

[^kdd-role]: KDD bundle, knowledge architect role profile v1.3.
[^kdd-agent]: KDD bundle, knowledge architect agent definition, with the ten skills.
[^kdd-agent-v2]: KDD bundle, knowledge architect agent definition with the five distillation kinds.
[^kdd-af]: KDD bundle, functional architect role profile.
[^adr-0033]: SDR-0022, decisions 3 and 4.
[^adr-0017]: ADR-0017, decisions 3 and 5.
[^adr-0024]: SDR-0017, decisions 6, 7 and 10.
[^adr-0031]: ADR-0031, decision 4.
