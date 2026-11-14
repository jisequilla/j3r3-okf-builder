---
type: Standard Decision
title: "SDR-0023: A domain bundle defines its operational kinds in base and holds their instances as bundles next to its layers, each naming its parent"
description: A bundle is either a domain bundle, whose knowledge never closes, or an operational bundle, a unit of work that opens and closes; the domain bundle's Domain Profile defines each operational kind (its directory, its states and the kinds it may hold) and a family of base/ says how that work is done; each instance is a full bundle stored in its kind's directory next to the layers, never inside base/, whose root index.md declares kind, state, parent and a declarative depends_on; lint recurses into instances; a closing instance distills its whole base/ one level up, each concept promoted, opened as a conflict or kept, and closes only once its open conflicts and questions are resolved or carried up; a closed one is frozen or extracted.
tags: [adr, standard, bundles, profile]
status: deprecated
decision_id: SDR-0023
formerly: ADR-0038
decision_status: superseded
supersedes:
superseded_by: /base/decisions/standard/SDR-0024-closing-operational-bundles.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: { by: human:jisequilla, at: 2026-11-10T22:34:50Z }
sources:
  - { id: fragment, resource: /fragments/2026-11-10-domain-and-operational-bundles.md, title: "Fragment: domain and operational bundles" }
  - { id: adr-0026, resource: /base/decisions/standard/SDR-0019-built-in-domain-profile.md }
  - { id: adr-0021, resource: /base/decisions/standard/SDR-0014-three-layers-with-open-questions.md }
  - { id: standard, resource: plugin/okf-builder/skills/okf-standard/references/OKF-STANDARD.md, title: "OKF standard, profile knowledge/3.0, §2" }
  - { id: spec, resource: plugin/okf-builder/skills/okf-standard/references/OKF-SPEC-v0.2.md, title: "OKF spec v0.2, §12" }
---

# Context

The standard assumes that `knowledge/` is one bundle. A subdirectory whose `index.md` declares its own `okf_version` is a nested bundle, which `okf-lint` skips with a notice and which nothing relates to the bundle around it[^standard].

Teams keep two kinds of knowledge. Some never closes: a domain, a system, a team's doctrine. Some belongs to a unit of work that opens, runs and closes: a request, an incident, a release and what it ships, an engagement. Mixing the second into `base/` gives lasting concepts a lifecycle they do not have, and loses the rule that what is born in a unit of work stays with it. One OKF implementation read on 2026-11-07 answers it with a repository manifest over several bundles and a declarative `depends_on`; its version lives in the manifest, so this standard's version detection misread one of its bundles[^fragment].

The owner, human:jisequilla, shaped the decision in answer to structured questions on 2026-11-07 and 2026-11-10, keeping it generic: an organization names its own kinds of work[^fragment].

# Decision

1. **A bundle is a domain bundle or an operational bundle.** A domain bundle holds knowledge that never closes. An operational bundle holds one unit of work, which opens and closes. The root `index.md` declares it with `kind`; a bundle without `kind` is a domain bundle, so every existing bundle keeps its meaning. Whether a bundle is open-ended or bounded follows from its kind and is never declared.
2. **The domain bundle defines each operational kind in its Domain Profile.** `base/profile.md` gains the key `kinds`. Each kind (`Request`, `Incident`, `Release`) extends the built-in abstract kind `Operational Bundle` and declares:

   | Key | Meaning |
   |---|---|
   | `extends` | `Operational Bundle`, or another kind of an extended profile |
   | `description` | What one unit of this work is |
   | `directory` | Where its instances live, relative to the bundle that holds them (`requests/`) |
   | `states` | States added between `open` and `closed`, which every kind has; `closed` is the only terminal state |
   | `holds` | The kinds an instance of this kind may hold (`Release` holds `[Request, Incident]`) |

   A kind is not a concept type: a bundle is not a concept, so kinds sit apart from `types`. The composition rules of ADR-0026 apply to them unchanged: an extension only adds, the same id from two sources is an error, and a reference that cannot be read is an error[^adr-0026]. How the work is done (its process, its closing, its terms and doctrine) is knowledge of the domain bundle: concepts in a directory of `base/` per kind, such as `base/requests/`, which `families` may declare.
3. **An instance is a full bundle in its kind's directory, next to the layers, never inside `base/`.** A request of the domain bundle lives at `knowledge/requests/<id>/`; a request a release ships lives at `knowledge/releases/<id>/requests/<id>/`. The root of a bundle holds, besides its reserved files and its three layers, the directory of each kind it may hold, with an `index.md` listing its instances and their states. An instance has the same layout at every depth: `index.md`, `log.md`, `project.md` describing the unit of work, a Conflict Log when it has one, `fragments/`, `base/` and `projections/`. A kind's `directory` never names a reserved file or a layer.
4. **The root `index.md` of an instance declares its metadata, and nothing else does.** Its frontmatter holds `okf_version` and `okf_profile`, as every bundle's does (spec §12)[^spec], and `kind`, `state`, `parent`, `closed_at` once closed, and `depends_on` when it has any:

   ```yaml
   okf_version: "0.2"
   okf_profile: "knowledge/3.0"
   kind: request
   state: open
   parent: ../..
   depends_on:
     - { bundle: ../../incidents/inc-0412 }
     - { repo: payments-service, bundle: knowledge, ref: v2.3.0 }
   ```

   Each bundle declares its own `okf_version`, so the nested-bundle detection of the standard keeps working and an extracted bundle describes itself. There is no separate `okf.yaml`.
5. **`parent` and `depends_on` are different relations.** `parent` is required on an instance and absent on a domain bundle: the bundle path of the bundle that holds it, the one it distills into, whose kind's `holds` must include this instance's kind. Lint reads it. `depends_on` lists other bundles this one refers to, each `{ bundle, repo?, ref? }`: lint checks its shape and shows it, and no tool resolves it.
6. **The profile in force for an instance** is the built-in profile, then the profile chain of the domain bundle that defines its kind, then the instance's own `base/profile.md` if it has one. An instance may add concept types for its own use; it never defines kinds, which live only in the domain bundle.
7. **A closing instance distills its whole `base/` one level up.** `okf-distill` reads every concept of the instance's `base/` against the parent bundle and proposes one outcome for each: **promote** (lasting knowledge, added to or updating the parent's `base/`), **conflict** (it contradicts the parent, opened in the parent's Conflict Log) or **stays** (specific to this unit of work, kept in the instance). A person approves the change set, which is kept as the instance's closing fragment, and each promoted concept cites the instance concept it came from. One level at a time: a request a release ships distills into the release, and the release into the domain bundle when it closes.
8. **An instance closes with no loose ends.** Before it closes, each open conflict in its Conflict Log and each open question in its `base/questions/` is resolved, or carried up into the parent as an open conflict or open question that links back to it. Lint reports an error for a closed instance that still holds an open conflict or an open question.
9. **A closed instance is frozen or extracted.** Closing sets `state: closed` and `closed_at`. A frozen instance stays where it is, is still checked by lint, and is never edited; `okf-review` lists any concept in it whose `generated.at` is later than `closed_at`. Lint does not read git. An extracted instance moves to its own repository, drops `parent`, and pins the definition of its kind with `extends: <path>@<commit>` in its `base/profile.md`.
10. **Lint recurses into instances by default.** Linting a domain bundle checks every instance found in the directories its kinds declare, each against the definition of its kind and reported as its own bundle; `--no-nested` skips them. A nested bundle outside any kind's directory keeps today's behaviour: one notice, linted on its own.
11. **Out of scope:** a repository-level manifest over several domain bundles, as a multi-module repository needs, is decided apart when a real repository needs it.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| `knowledge/index.md` as a repository manifest over 1..n bundles | Matches the implementation that prompted this; one place for shared settings | `knowledge/` stops being a bundle with its own layers; puts a version outside each bundle | The domain bundle holds lasting knowledge and its units of work; the manifest is deferred |
| Instances inside `base/<kind>/` | The definition and the instances in one place | `fragments/` inside `base/` breaks the layer rule; mixes lifecycles into `base/` | The definition goes in `base/`, the instances next to the layers |
| Kinds as local concept types in `types` | No new key in the Domain Profile | A bundle is not a concept; a kind's directory, states and `holds` fit no field of a type | Kept apart as `kinds` |
| A `lifecycle` field on each instance | Readable without the parent's profile | Repeats what the kind implies; lint must check that the two agree | The kind implies it; an extracted bundle pins its kind |
| An `okf.yaml` per bundle | Cheap detection; configuration apart from prose | States `okf_version` outside the spec's place, or twice | The root `index.md` already holds it; `okf.yaml` is kept for the repository manifest |
| The parent as one entry of `depends_on` | One key | Every tool must find the parent in a list; mixes a resolved relation with declarative ones | Two keys, two meanings |
| Distilling only a closing fragment written as a summary | Light; one record per closing | What the summary leaves out never reaches the parent | The whole `base/` is read, each concept sorted |
| Moving every concept of the instance into the parent | Nothing is left behind | Floods the domain bundle with what belongs to one unit of work | The distillation sorts; case knowledge stays |
| Closing with open conflicts or questions, with a warning | No step blocks a closing | Frozen bundles keep unresolved items nobody sees again | Resolved or carried up before closing |
| Lint enforcing frozen bundles through git | Strict | Lint depends on git history | `closed_at` and `okf-review` suffice |
| Instances linted only on their own | Today's behaviour | A whole tree needs one command per instance | Recursion by default, with `--no-nested` |
| A fixed directory for every instance, such as `cases/<kind>/` | One place to look | Imposes a name and a level on every organization | Each kind names its directory |

# Consequences

- Positive: lasting knowledge and units of work stay apart while staying in one tree; an organization names its own kinds of work in its Domain Profile; one lint run checks a domain bundle and every unit of work in it; a unit of work can leave the tree and still describe itself; what a unit of work taught reaches the domain, with its contradictions opened as conflicts, and nothing unresolved is frozen away.
- Negative / accepted debt: the Domain Profile gains a key and the built-in profile an abstract kind; the bundle root may hold directories beyond its layers; frozen is a convention `okf-review` reports, not a guarantee; two bundles may name each other in `depends_on` with nothing checking that the target exists.
- Follow-up actions: the standard's §2 (bundle root, nested bundles) and §4.1 (the `kinds` key); `okf_lint` reads `kind`, `state`, `parent`, `closed_at` and `depends_on`, checks them against the kinds in force and recurses into instances; `okf-index` lists each kind's instances and stops walking into nested bundles (ticket okf-4j8); `okf-init` creates an instance of a kind; `okf-distill` distills a closing instance's whole `base/` into its parent; lint checks that a closed instance holds no open conflict or open question; `okf-review` lists concepts changed after `closed_at`; the example bundle gains a kind and an instance; the repository-level manifest is ticket okf-e2k.

# Related

* [ADR-0026: The built-in Domain Profile](/base/decisions/standard/SDR-0019-built-in-domain-profile.md)
* [ADR-0021: Three layers with open questions](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md)
* [ADR-0028: Where things go](/base/decisions/DEC-0003-where-things-go.md)

[^fragment]: 2026-11-10 · Domain and operational bundles, Record.
[^standard]: OKF standard, profile knowledge/3.0, §2 (nested bundle).
[^spec]: OKF spec v0.2, §12.
[^adr-0026]: ADR-0026, decisions 3 and 4.
