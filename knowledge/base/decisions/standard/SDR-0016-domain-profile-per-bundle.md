---
type: Standard Decision
title: "SDR-0016: A bundle declares its taxonomy in one Domain Profile, with families per directory, composition rules and profiles shared by reference"
description: A bundle's base/profile.md of type Domain Profile declares its types, typed fields, families (a schema per directory), questions and optional aliases, extends shared profiles by reference and never copies them, and follows written composition rules (an extension only adds, a duplicate id is an error, forbidden, fixed, by_type, named rules, validator delegation); lint and the skills read it.
tags: [adr, standard, profile, taxonomy]
status: deprecated
decision_id: SDR-0016
formerly: ADR-0023
decision_status: superseded
superseded_by: /base/decisions/standard/SDR-0019-built-in-domain-profile.md
supersedes: /base/decisions/standard/SDR-0013-domain-profiles.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
  - { id: tool, resource: /fragments/2026-11-02-migration-tool-okf-review.md, title: "Fragment: what a long-running OKF implementation teaches" }
  - { id: spec, resource: /base/references/okf-spec-google.md, title: "OKF specification v0.2, §4 extensions, §8 index files, §11 conformance" }
---

# Context

[ADR-0020](/base/decisions/standard/SDR-0013-domain-profiles.md) let a domain declare its taxonomy as data, in a `Domain Profile` concept (`profile.md`) placed in any directory under `base/` and extended by profiles lower in the tree, rather than in `index.md`, which OKF v0.2 does not allow to carry frontmatter[^spec]. It declared types, typed fields, questions, dependencies and aliases[^bundles].

A migration tool that has run twelve OKF bundles on nine profiles for months shows what a validator that knows no type by name ends up needing[^tool]: written composition rules (an extension only adds; the same id from two sources is a structural error), `forbidden` keys with a reason, `fixed` values, overrides per type, a few named rules for conditions across fields, delegation of a type to another validator, profiles shared by reference and never copied ("a copy would diverge"), and a path from a local profile to a shared one when a second corpus wants it. It scopes one profile per bundle and varies by folder inside it (`layout: families`), and never needed inheritance through the directory tree. The owner chose that scope, kept `aliases` as optional, and kept the profile a concept. Nobody had implemented ADR-0020 yet.

# Decision

1. **A bundle declares its taxonomy in one concept of type `Domain Profile`, at `base/profile.md`.** It is an ordinary concept: `generated`, `sources`, `status`; a person may verify it; it is deprecated and superseded like an ADR; `index.md` lists it. A bundle without one uses the profile's types as they are.
2. **Its frontmatter declares**:

   | Key | Meaning |
   |---|---|
   | `extends` | Shared profiles this one builds on, by reference: a bundle path, or a repository path or URL pinned to a commit. Never copied |
   | `types` | Each local type: `extends` (a profile type or a type of an extended profile), `description`, `fields` |
   | `fields` (per type) | Each field: `type` (`string`, `integer`, `boolean`, `date`, `list`, `enum`, `path`), `of` for lists, `values` for enums, `required`, `note` |
   | `families` | A schema per directory under `base/`: for each directory, the types allowed there and any `required`, `fixed` or `forbidden` that apply only there |
   | `forbidden` | Keys that must not appear, each with its reason |
   | `fixed` | Keys whose value is fixed, with that value |
   | `by_type` | Overrides of `required`, `fixed` or `forbidden` for one type |
   | `rules` | Named conditions across fields, few and declarative: `{ name, when: { field: value }, require: [fields] }` |
   | `validator` | Types or families validated by another tool: the command, which `okf_lint` runs and reports |
   | `questions` | The questions the bundle answers, each mapped to a `field` (`Type.field`) or a `concept` (a bundle path) |
   | `aliases` | Optional. Local names for the profile's types, fields and values (`Fragmento` → `Knowledge Fragment`; `ingerido: true` → `distillation_status: distilled`) |

   The body explains the taxonomy and justifies each type and field with its sources.
3. **Composition rules**:
   - an extension only adds: a type, field, enum value or rule defined higher up is never redefined or removed;
   - the same id (type, field, family or rule) from two sources is a structural error, not an override;
   - layers merge from general to specific: the profile's types, then each extended profile in order, then the bundle's own declarations, then `families`, then `by_type`;
   - a reference to a profile that cannot be read is an error.
4. **The tools read the profile instead of a fixed list.** `okf_lint` validates each concept against the profile in force for its directory: a missing required field, a value outside its enum, a forbidden key, a wrong fixed value or a broken named rule is an error, and a key no profile declares is a warning. `okf_lint --profiles` lists what is in force for a path. `okf-distill`, `okf-review` and `okf-ask` resolve aliases. A question mapped to a field is answered from the frontmatter: a concept that lacks the field is the gap.
5. **`base/` may be organised by type, as `okf-init` creates it, or by domain**; `families` says what each directory holds. The usual directory of each type in the standard is a default, not a rule.
6. **Types emerge from need, decided by a person.** A concept first fits an existing type; if one almost fits, a new type is proposed; if none fits, the bundle declares a local one. A local profile is promoted to a shared one, by a pull request to the shared profile's repository, when a second bundle wants it. Friction with a profile is raised to a person, never resolved by relaxing an enum. Each type and field is justified in the profile's body.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| ADR-0020: a profile in any directory, extended down the tree | Each domain owns its own file | Every reader resolves a chain of profiles; the tool with twelve bundles never needed it | One file per bundle, with families, is simpler to read and check |
| Profiles as YAML manifests or files outside the bundle, as the reviewed tool keeps them | Shareable without OKF | Not knowledge: no sources, no verification, no deprecation | A taxonomy is knowledge; sharing by reference covers reuse |
| The taxonomy in `index.md` frontmatter | Next to what it describes | Breaks OKF v0.2 conformance[^spec] | Conformance matters more |
| Drop `aliases`, as the reviewed tool does | Smaller schema | The skills cannot read bundles with local names | Kept, optional |
| Copy shared profiles into each bundle | Self-contained bundles | Copies diverge | Referenced and pinned to a commit instead |

# Consequences

- Positive: one place to read a bundle's taxonomy; composition that cannot silently override; profiles reused across bundles and repositories; lint checks what the bundle declares and can hand a family to its own validator.
- Negative / accepted debt: a larger schema to implement and document; references pinned to a commit must be updated deliberately; a wrong profile spreads its errors to every concept it covers until a person reviews it.
- Follow-up actions: the `Domain Profile` type in the standard and a `profile.md` template; profile resolution, composition rules and `--profiles` in `okf_lint.py` with tests; alias resolution in `okf-distill`, `okf-review` and `okf-ask`; `okf-capture` offers the types in force.

# Related

* [ADR-0020: Domain Profiles](/base/decisions/standard/SDR-0013-domain-profiles.md)
* [ADR-0021: Three layers, with open questions](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md)
* [ADR-0022: Knowledge projections, drift by nature](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md)

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
[^tool]: Fragment of 2026-11-02, the review of a long-running OKF implementation and its design meetings.
[^spec]: OKF v0.2: §4 (producers may add keys), §8 (index files carry no frontmatter except the root's `okf_version`), §11 (conformance).
