---
type: Architecture Decision
title: "ADR-0027: The owner of an operational concept is a string; Actor stays as the OKF spec defines it"
description: On API, Metric, Playbook, Policy, Runbook, System and Table, owner is a string that names a team or a person, so team:<team> is valid; an Open Question's owner stays an actor, and the actor convention stays exactly the spec's, with no team prefix.
tags: [adr, standard, profile, actor]
status: draft
adr_id: ADR-0027
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T21:00:16Z }
sources:
  - { id: spec-actor, resource: plugin/okf-builder/skills/okf-standard/references/OKF-SPEC-v0.2.md, title: "OKF spec v0.2 §2 (Actor) and §7 (Actor convention)" }
  - { id: types, resource: standard/OKF-STANDARD.md, title: "OKF standard §4: Profile type vocabulary" }
  - { id: adr-0026, resource: /base/decisions/ADR-0026-built-in-domain-profile.md }
  - { id: templates, resource: plugin/okf-builder/skills/okf-standard/templates/ }
---

# Context

[ADR-0026](/base/decisions/ADR-0026-built-in-domain-profile.md) made the standard's types a built-in Domain Profile, with `actor` as a field type that "follows the actor convention"[^adr-0026]. Building it declared `owner` as an actor on System, API, Table, Metric, Runbook, Playbook and Policy, as §4 of the standard then described it[^types].

The sweep of every template against the built-in profile, in PR #52, found that seven templates write `owner: team:{{team}}`: api, metric, playbook, policy, runbook, system and table[^templates]. `team:<id>` is not an actor. The OKF spec v0.2 defines an Actor as "a string identifying who or what performed an action", in three forms only: `<producer>/<version>` for agents and tools, `human:<id>` for a person, `process:<id>` for an automated process; the fields that record an identity are `generated.by` and `verified[].by`, and consumers classify trust by the `human:` prefix[^spec-actor]. A filled template therefore failed its own type's check in every bundle with a `base/profile.md`.

The owner of a system, a contract or a procedure is usually a team, and it is not the author of any content: it says who answers for the thing, not who wrote or verified the concept. An Open Question is different: its `owner` names the person who must get it answered, and the skills already ask for a `human:<id>` there.

Asked in a structured question, the repository's owner chose to keep the actor as the spec defines it and to make these owners strings.

# Decision

1. **The actor convention stays exactly as the OKF spec v0.2 defines it** (§2, §7): `<producer>/<version>`, `human:<id>`, `process:<id>`. The standard adds no `team:` form and no other prefix.
2. **On API, Metric, Playbook, Policy, Runbook, System and Table, `owner` is a string**: who owns it, a team or a person, in whatever form the team uses (`team:payments`, `human:ann`, `Payments`). Standard §4 and the built-in profile declare it `{ type: string }`. The templates keep `owner: team:{{team}}`.
3. **An Open Question's `owner` stays an actor**, required at level `warn` with `BAD_ACTOR` for another form, because it names the person who answers the question.
4. This decision refines ADR-0026, which stands: ADR-0026 declares the `actor` field type and leaves the type of each field to the standard's §4.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| `owner` is a string on the seven types | Templates unchanged; a team can own a thing; the actor convention stays the spec's | Lint no longer checks the form of an owner | Chosen |
| Add a `team:<id>` actor as a profile extension, recorded as a deviation from the spec | Owners keep a checked form; templates unchanged | A v0.2 consumer rejects `team:x` where an actor is expected (`generated.by`, `verified[].by`), so a redefined actor breaks upstream conformance; the deviation leaks from `owner` into every actor field | Breaks conformance with the spec |
| Keep `owner` an actor and require `human:<id>` owners, changing the templates | Every owner is a checked identity | A team cannot own a system, a contract or a procedure; the owner becomes one person who leaves | Ownership in practice is by team |

# Consequences

- Positive: every template lints against the built-in profile with no profile finding; the actor convention is the spec's, so any v0.2 consumer reads every actor field of a bundle; a team owns what it owns.
- Negative / accepted debt: lint checks only that an owner is text, not who it names; owners in a bundle may use several forms.
- Follow-up actions: standard §4 (both copies) and the built-in profile declare `owner` a string on the seven types; the template sweep test pins zero profile findings.

# Related

* [ADR-0026: The standard's own types are a built-in Domain Profile](/base/decisions/ADR-0026-built-in-domain-profile.md)
* [ADR-0021: Three layers, with open questions](/base/decisions/ADR-0021-three-layers-with-open-questions.md)
* [ADR-0025: Verification recorded by question](/base/decisions/ADR-0025-verification-recorded-by-question.md)

[^adr-0026]: ADR-0026, decision 3.
[^types]: OKF standard §4, the rows of System, API, Table, Metric, Runbook, Playbook and Policy.
[^templates]: The api, metric, playbook, policy, runbook, system and table templates, each with `owner: team:{{team}}`.
[^spec-actor]: OKF spec v0.2, §2 (definition of Actor) and §7 (Actor convention).
