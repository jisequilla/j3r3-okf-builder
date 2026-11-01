---
type: Architecture Decision
title: "ADR-0020: A domain declares its own taxonomy in a Domain Profile concept, which lint and the skills read"
description: A directory under base/ may hold a profile.md of type Domain Profile that declares the domain's types (each extending a profile type), their typed fields, the questions the domain answers, its dependencies and aliases for local names; it applies to its directory and below, and the tools read it instead of a fixed list.
tags: [adr, standard, profile, taxonomy]
status: draft
adr_id: ADR-0020
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:45:00Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
  - { id: spec, resource: /references/okf-spec-google.md, title: "OKF specification v0.2, §4 extensions, §8 index files, §11 conformance" }
  - { id: adr-0018, resource: /decisions/ADR-0018-three-layers-fragments-base-projections.md }
---

# Context

The profile fixes one type vocabulary (§4 of the standard), and the tools key on it: `okf-distill`, `okf-review` and `okf-ask` look for `Knowledge Fragment`, `distillation_status` or `Architecture Decision` by name. None of the eleven explored bundles uses that vocabulary as it is. Each domain defines its own types and fields, and the latest bundles declare them as data, per module: the types (each may extend a common type), their typed fields, the questions the module answers mapped to a field or a concept, and the modules it depends on. Their validator knows no type by name, and a new type appears only when three notes share a shape[^bundles]. On those bundles the skills cannot see the fragments, decisions or open questions, and lint reports mostly false positives[^bundles].

The fragment records the owner's choice to declare the taxonomy in the frontmatter of each domain directory's `index.md`[^bundles]. OKF v0.2 does not allow it: "Index files contain no frontmatter, with one exception: a bundle-root `index.md` MAY carry an `okf_version` key", and a bundle is conformant only if its reserved files follow that structure[^spec]. The spec does let producers add any key to a concept and requires consumers to tolerate unknown keys and types[^spec]. While distilling, the owner chose to declare the taxonomy as a concept instead.

# Decision

1. **A domain declares its taxonomy in a concept of type `Domain Profile`**, named `profile.md`, in the domain's directory under `base/`. It is an ordinary concept: `generated`, `sources`, `status`, a person may verify it, it is deprecated and superseded like an ADR, and `index.md` lists it. A `base/profile.md` applies to the whole base.
2. **Its frontmatter declares**:

   | Key | Meaning |
   |---|---|
   | `types` | Each local type: `extends` (a profile type, or another type of a profile above), `description`, and `fields` |
   | `fields` (per type) | Each field: `type` (`string`, `integer`, `boolean`, `date`, `list`, `enum`, `path`), `of` for lists, `values` for enums, `required`, `note` |
   | `questions` | The questions the domain answers, each mapped to a `field` (`Type.field`) or a `concept` (a bundle path) |
   | `depends_on` | The other Domain Profiles this one builds on, as bundle paths |
   | `aliases` | Local names for the profile's types, fields and values (`Fragmento` → `Knowledge Fragment`; `ingerido: true` → `distillation_status: distilled`) |

   The body explains the domain and justifies each type and field with its sources.
3. **Scope**: a Domain Profile applies to the concepts of its directory and its subdirectories. A profile lower in the tree extends the ones above it; a local type or field never redefines a profile type or field, it extends it.
4. **The tools read the profiles instead of a fixed list.** `okf_lint` validates each concept against the types and fields in force for its directory: a missing required field or a value outside its enum is an error, a key no profile declares is a warning. `okf-distill`, `okf-review` and `okf-ask` resolve aliases, so a local fragment type or supersession field is handled as the profile's. A question mapped to a field is answered from the frontmatter: a concept that lacks the field is the gap.
5. **`base/` may be organised by type, as `okf-init` creates it, or by domain.** The usual directory of each type in the standard's §4 table is a default, not a rule.
6. **Types emerge from need.** A local type is declared when about three concepts share its shape, and each type and field is justified in the profile's body with its sources.
7. **Bundles without a Domain Profile** keep the profile's types as they are.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| The taxonomy in the frontmatter of each directory's `index.md` | No new type; next to what it describes | Breaks OKF v0.2 conformance: index files carry no frontmatter except the root's `okf_version`[^spec] | Conformance matters more than proximity |
| A `manifest.yaml` per domain, as the latest explored bundles do | JSON Schema can validate it; OKF tools never see it | Not knowledge: no sources, no verification, no deprecation | A taxonomy is knowledge about the domain |
| Extend the fixed type table in the standard for every domain | One place | The standard grows with every domain; local names still unknown | Domains own their taxonomies |
| Local types redefine profile types | Full freedom | The skills lose the semantics they rely on (a fragment, a supersession) | A local type extends; aliases map names |

# Consequences

- Positive: domains get their own vocabulary without leaving OKF; lint checks what each domain declares; the skills work on bundles with local names; coverage questions become frontmatter queries.
- Negative / accepted debt: `okf_lint` and the skills gain a resolution step (the profiles in force for a directory); a profile can be wrong, and its errors spread to every concept below it until a person reviews it.
- Follow-up actions: the `Domain Profile` type in the standard (§4) and a `profile.md` template; profile resolution in `okf_lint.py` and its tests; alias resolution in `okf-distill`, `okf-review` and `okf-ask`; `okf-capture` offers the local types in force; land it with profile knowledge/3.0 ([ADR-0018](/decisions/ADR-0018-three-layers-fragments-base-projections.md)).

# Related

* [ADR-0018: Three layers: fragments, base and projections](/decisions/ADR-0018-three-layers-fragments-base-projections.md)
* [ADR-0019: Knowledge projections](/decisions/ADR-0019-knowledge-projections.md)

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
[^spec]: OKF v0.2: §4 (producers may add keys), §8 (index files carry no frontmatter except the root's `okf_version`), §11 (conformance).
