---
type: Standard Decision
title: "SDR-0019: The standard's own types are a built-in Domain Profile, the first layer under each bundle's profile, with a level per requirement and typed actors and timestamps"
description: A bundle's base/profile.md declares its taxonomy as in ADR-0023, on top of a built-in Domain Profile shipped with okf-standard that declares the standard's types; requirements carry a level (error or warn), field types add actor, datetime and date_or_datetime, checks across concepts stay in code, and lint reads references locally, runs validators only on request, resolves aliases and warns on undeclared keys only in bundles with a profile.
tags: [adr, standard, profile, taxonomy]
status: stable
decision_id: SDR-0019
formerly: ADR-0026
decision_status: accepted
supersedes: /base/decisions/standard/SDR-0016-domain-profile-per-bundle.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: [{ by: human:jisequilla, at: 2026-11-08T13:54:06Z }, { by: human:jisequilla, at: 2026-11-14T17:26:55Z }]
sources:
  - { id: adr-0023, resource: /base/decisions/standard/SDR-0016-domain-profile-per-bundle.md }
  - { id: tool, resource: /fragments/2026-11-02-migration-tool-okf-review.md, title: "Fragment: what a long-running OKF implementation teaches" }
---

# Context

[ADR-0023](/base/decisions/standard/SDR-0016-domain-profile-per-bundle.md) gave each bundle one `Domain Profile` at `base/profile.md`, with typed fields, families per directory, composition rules and profiles shared by reference, and had `okf_lint` validate each concept against it[^adr-0023]. It left the standard's own types (Knowledge Fragment, Conflict Log, Open Question, Attested Computation and the rest of §4) where they are: checks written in code that know each type by name. The reviewed migration tool shows where that ends: a validator that knows no type by name, reading every type from declarations[^tool].

While scoping the implementation, the owner chose that path: the standard's types become data too, so one engine checks every type and a local type extends a standard one the same way it extends a shared profile. ADR-0023's schema cannot express today's checks as they are:

- every breach of a profile is an error, but a fragment without `participants` or a question without `owner` is a warning today, and must stay one;
- its field types (`string`, `integer`, `boolean`, `date`, `list`, `enum`, `path`) have no actor (`human:<id>`), no ISO 8601 datetime with an offset, and no "a date or a datetime" as `occurred_at` and `review_on` accept;
- some checks are not about one field of one concept: at most one Conflict Log per bundle, where concepts may live in a 3.0 bundle, when an open question is due, the single fence of an Attested Computation.

Scoping also settled four points ADR-0023 left open: how `extends` is read, whether lint runs a declared validator, whether lint resolves aliases, and which bundles get the warning for undeclared keys. Once a built-in profile is always present, that warning would fire on every bundle that uses any key of its own.

# Decision

1. **A bundle declares its taxonomy in one concept of type `Domain Profile`, at `base/profile.md`.** It is an ordinary concept: `generated`, `sources`, `status`; a person may verify it; it is deprecated and superseded like an ADR; `index.md` lists it. Profile knowledge/3.0 only: a `profile.md` in a 2.0 bundle is ignored with a notice to migrate, and a `Domain Profile` anywhere else is an error.
2. **The standard's types are a built-in Domain Profile**, shipped with the `okf-standard` skill and versioned with the plugin. It declares each type of the standard's §4 with its fields, levels and usual directory. It is the first layer of every bundle's profile, and a bundle without `base/profile.md` is checked against it alone. Its content changes only with the standard.
3. **The frontmatter of a Domain Profile declares**:

   | Key | Meaning |
   |---|---|
   | `extends` | Shared profiles this one builds on, by reference: a bundle path, or a repository path pinned to a commit (`<path>@<commit>`). Never copied |
   | `types` | Each type: `extends` (a type of the built-in profile or of an extended profile), `description`, `fields` |
   | `fields` (per type) | Each field: `type` (`string`, `integer`, `boolean`, `date`, `datetime`, `date_or_datetime`, `actor`, `list`, `enum`, `path`), `of` for lists, `values` for enums, `required`, `level` (`error`, the default, or `warn`), `note` |
   | `families` | A schema per directory under `base/`: for each directory, the types allowed there and any `required`, `fixed` or `forbidden` that apply only there |
   | `forbidden` | Keys that must not appear, each with its reason and level |
   | `fixed` | Keys whose value is fixed, with that value and level |
   | `by_type` | Overrides of `required`, `fixed` or `forbidden` for one type |
   | `rules` | Named conditions across fields, few and declarative: `{ name, when: { field: value }, require: [fields], level }` |
   | `validator` | Types or families validated by another tool: the command |
   | `questions` | The questions the bundle answers, each mapped to a `field` (`Type.field`) or a `concept` (a bundle path) |
   | `aliases` | Optional. Local names for types, fields and values (`Fragmento` → `Knowledge Fragment`; `ingerido: true` → `distillation_status: distilled`) |

   `datetime` is ISO 8601 with an explicit offset, `date_or_datetime` also accepts `YYYY-MM-DD`, and `actor` follows the actor convention. The body explains the taxonomy and justifies each type and field with its sources.
4. **Composition rules**:
   - an extension only adds: a type, field, enum value or rule defined higher up is never redefined or removed, and a level is never lowered;
   - the same id (type, field, family or rule) from two sources is a structural error, not an override;
   - layers merge from general to specific: the built-in profile, then each extended profile in order, then the bundle's own declarations, then `families`, then `by_type`;
   - a reference that cannot be read is an error. Lint reads references locally, never over the network: a bundle path from the bundle, `<path>@<commit>` from the bundle's own repository. A URL is not read; it is an error that names the missing support.
5. **The tools read the profile instead of a fixed list.** `okf_lint` validates each concept against what is in force for its directory: each breach is reported at its declared level. A key nobody declares is a warning only in a bundle that has a `base/profile.md`. `okf_lint --profiles` lists what is in force for a path and which layer declared each item. Lint and the skills resolve aliases, so a local name gets the checks of the type, field or value it stands for. A question mapped to a field is answered from the frontmatter: a concept that lacks the field is the gap.
6. **Checks across concepts or over a body stay in code**: at most one Conflict Log per bundle; the layer rule of a 3.0 bundle; an open question past its `review_on`; the single fence of an Attested Computation; the structure of `index.md` and `log.md`. They apply to a local type through the standard type it extends.
7. **Validators run only on request.** `okf_lint` runs a profile's `validator` commands only with `--run-validators`, and reports their failures with secrets masked. Without the flag it notes each validator it did not run. A bundle's content never runs a command by default, and the skills ask the person before passing the flag.
8. **`base/` may be organised by type, as `okf-init` creates it, or by domain**; `families` says what each directory holds. The usual directory of each type is a default, not a rule.
9. **Types emerge from need, decided by a person.** A concept first fits an existing type; if one almost fits, a new type is proposed; if none fits, the bundle declares a local one. A local profile is promoted to a shared one, by a pull request to the shared profile's repository, when a second bundle wants it. Friction with a profile is raised to a person, never resolved by relaxing an enum or a level. Each type and field is justified in the profile's body.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| ADR-0023 as it is: standard types in code, bundle types in data | No port of working checks | Two ways to check a type; a local type extends a standard one through code it cannot see | The owner chose one engine for every type |
| Every breach an error, as ADR-0023 says | One level | Today's warnings (a fragment without `participants`) become errors and break every existing bundle | A level per requirement keeps them |
| Express every check as data, cross-concept ones included | Nothing in code | Needs a query language in the profile; the few checks that span concepts are clearer in code | Field checks in data, the rest in code |
| Read `extends` URLs pinned to a commit | Profiles in any repository | Lint depends on the network and on the remote | Local references now; URLs stay unread until a decision adds them |
| Run validators always | What ADR-0023 says | Opening a bundle runs its commands | On request only |
| Warn on undeclared keys in every bundle | One rule | With the built-in profile always present, every bundle with its own keys gets warnings | Only where the bundle declares a profile |

# Consequences

- Positive: one engine checks every type; a local type extends a standard one exactly as it extends a shared profile; `--profiles` shows the standard's own types too; today's warnings stay warnings.
- Negative / accepted debt: today's per-type checks must be ported to the built-in profile without changing what lint reports; the schema grows by a level and three field types; the standard's §4 and the built-in profile must be kept in step.
- Follow-up actions: the standard (§2, §4, §6, §7) and a `profile.md` template; the built-in profile; profile loading, composition and `--profiles`; the port of today's per-type checks, with lint output unchanged on every existing test and fixture; concept checks against the profile, aliases and validators; the skills (capture, fragment, distill, review, ask, lint) and the agent.

# Related

* [ADR-0023: One Domain Profile per bundle](/base/decisions/standard/SDR-0016-domain-profile-per-bundle.md)
* [ADR-0021: Three layers, with open questions](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md)
* [ADR-0022: Knowledge projections, drift by nature](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md)

[^adr-0023]: ADR-0023, decisions 1 to 6.
[^tool]: Fragment of 2026-11-02, the review of a long-running OKF implementation and its design meetings.
