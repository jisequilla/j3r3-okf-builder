---
type: Standard Decision
title: "SDR-0025: A decision is a Decision; Architecture Decision is one kind of it, and each kind has its own folder, prefix and sequence"
description: The standard gains an abstract built-in type Decision that Architecture Decision extends, with no catalogue of kinds; each decision type declares its folder and prefix in the profile, has its own template and numbers on its own sequence; this repository declares a local Standard Decision, keeps plain Decision for how the repo works, and moves and renumbers the 30 decisions that are not about the plugin's architecture.
tags: [adr, standard, decisions, profile, types]
status: deprecated
decision_id: SDR-0025
formerly: ADR-0040
decision_status: superseded
supersedes:
superseded_by: /base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:39:38Z }
verified: { by: human:jisequilla, at: 2026-11-13T20:05:02Z }
sources:
  - { id: fragment, resource: /fragments/2026-11-13-decision-types-beyond-adr.md, title: "2026-11-13 · Not every decision is an Architecture Decision, and how the standard and this repo should type decisions" }
  - { id: answers, resource: /fragments/2026-11-13-decision-types-identity-and-existing-files.md, title: "2026-11-13 · Decision types, the owner's answers on where a kind's folder and prefix are declared and on moving the 29 existing ADRs" }
  - { id: adr-0008, resource: /base/decisions/DEC-0001-dogfooding.md }
  - { id: adr-0026, resource: /base/decisions/standard/SDR-0019-built-in-domain-profile.md }
  - { id: adr-0039, resource: /base/decisions/standard/SDR-0024-closing-operational-bundles.md }
  - { id: standard, resource: plugin/okf-builder/skills/okf-standard/references/OKF-STANDARD.md, title: "OKF standard, §2 (the usual directory of a type is a default, not a rule), §4 (type vocabulary) and §6 (content change and human review)" }
---

# Context

The standard has one type for a decision, `Architecture Decision`, in `base/decisions/` with an `adr_id` and the file name `ADR-NNNN-slug.md`[^standard]. This bundle records every decision there, as [ADR-0008](/base/decisions/DEC-0001-dogfooding.md) says: "the project's decisions are ADRs"[^adr-0008].

The name is wrong for most of what the type holds, while its shape is right. Sorting this bundle's 39 decisions by what each one decides, from its title and description, gives[^fragment]:

| What the decision is about | Count | ADRs |
|---|---|---|
| The standard itself: format, layers, types, fields, rules a bundle must follow | 24 | 0001, 0002, 0003, 0004, 0005, 0010, 0012, 0014, 0015, 0016, 0018, 0019, 0020, 0021, 0022, 0023, 0024, 0025, 0026, 0027, 0029, 0033, 0038, 0039 |
| How the plugin is built and shipped: scripts, skills, agents, packages | 10 | 0006, 0007, 0011, 0013, 0017, 0030, 0031, 0032, 0034, 0037 |
| How the repo works: build runner, releases, tickets, dogfooding, where files go | 5 | 0008, 0009, 0028, 0035, 0036 |

Only the ten about the plugin are architecture decisions. The other 29 share the shape of one (context, alternatives, consequences, a body that is superseded and never edited) and not its subject.

One type for every decision does not scale. The standard covers domain bundles and the operational bundles they hold, such as a request, an incident or a release ([ADR-0039](/base/decisions/standard/SDR-0024-closing-operational-bundles.md))[^adr-0039]. Each of those units of work produces decisions of its own (a request is approved or rejected, an incident ends in a rollback), and they are not about architecture[^fragment]: the more instances a bundle holds, the more of its decisions carry a name that says the wrong thing. Today a bundle that wants another kind of decision with the fields and the rules of one declares a local type that extends `Architecture Decision`, which says that a product decision is a kind of architecture decision[^fragment]; a local type that extends nothing gets none of them.

Which kinds of decision exist differs by organization: the three found here are this repository's, and another team would have product, commercial or governance decisions. The standard already treats work that way: it ships only the abstract kind `Operational Bundle` and leaves the kinds to each bundle's Domain Profile[^adr-0039].

Three more forces shape how a kind of decision is named and filed[^fragment][^answers]:

- **The file name is what people cite.** A decision is referred to by its identifier in other concepts, in logs and in pull requests, so one prefix for every kind repeats the wrong name in each citation, and one shared sequence ties the numbering of a kind to decisions that have nothing to do with it.
- **Two naming schemes side by side cost every reader.** If the existing decisions kept their names and only new ones took the new scheme, a reader would need to know when a decision was written to know what its name means, and this repository's catalogue, the first example of the standard in use, would show the old scheme for most of its content.
- **The folders are how a person and an agent find decisions.** With every decision under one folder and each kind in a subfolder of it, the tree shows which types are decisions, and a new kind is one more subfolder, with no special place for architecture.

# Decision

1. **The standard gains an abstract built-in type `Decision`**, a record of something decided, with its context, the alternatives considered and its consequences. It carries what every decision shares: `decision_status` (proposed / accepted / superseded / rejected), `supersedes`, `superseded_by` and an identifier, the prefix of its file name. Its body is never edited after it is accepted; a decision that changes is a new decision that supersedes it. Every rule the standard and the skills state for an Architecture Decision (the audit never fixes a finding by editing its body, a refutation is a new decision with `supersedes`, the Obsidian Decisions view) is stated for `Decision` and reaches every type that extends it.
2. **`Architecture Decision` extends `Decision`** and keeps its name, its `adr_id` and its `ADR` prefix. It is the decision about how a system is built.
3. **The standard ships no other kind of decision.** A bundle declares the kinds it needs (product, business, governance, the decisions of an operational bundle) as local types that extend `Decision` in its Domain Profile, as it declares its operational kinds. A decision that fits no declared kind is a plain `Decision`.
4. **Each decision type has its own folder, prefix and sequence.** The type's declaration in the profile (the built-in Domain Profile for `Decision` and `Architecture Decision`, the bundle's `base/profile.md` for a local kind) names its directory and its prefix, and each type has its own template, whose file name and identifier follow that declaration. A decision is named `<PREFIX>-NNNN-slug.md`, NNNN the highest number its prefix was ever given in the bundle plus one, so a number is never reused (decision 8).
5. **The folders mirror the types.** The usual directory of `Decision` is `base/decisions/`, with the prefix `DEC`; a type that extends it lives in a subfolder: `Architecture Decision` in `base/decisions/architecture/`. The usual directory of a type remains a default, not a rule[^standard]: a bundle whose ADRs stay in `base/decisions/` still passes lint, and moving them is offered by `okf-migrate`, never forced.
6. **This repository declares one local type, `Standard Decision`**, for a decision about what the standard says, in `base/decisions/standard/` with the prefix `SDR`. A decision about how the repo works is a plain `Decision`. No other kind is added until one is needed.
7. **The 30 decisions that are not architecture decisions are retyped, moved and renumbered** in their original order: the 24 about the standard and this one become `SDR-0001` to `SDR-0025`, and the 5 about how the repo works `DEC-0001` to `DEC-0005`. The ten architecture decisions move to `base/decisions/architecture/` and keep their numbers. Bodies are not edited; links and `sources` that point to a moved decision are rewritten, except inside a fragment's `# Record`, which is immutable.
8. **An old number stays resolvable.** Each moved decision records the identifier it had (`ADR-0033`) in a field of its own, and the table below is the register of the move. The numbers `ADR-0001` to `ADR-0040` are never given to another decision: the next architecture decision is `ADR-0041`.
9. **This replaces the sentence of ADR-0008 that the project's decisions are ADRs**[^adr-0008]: they are decisions, of the type that says what each one is about. The rest of ADR-0008 stands.

# The move

The kind of each decision was read from its title and description; the build confirms each against its body before moving it, and a decision that spans two kinds takes the kind of its main subject.

| Was | Becomes | | Was | Becomes | | Was | Becomes |
|---|---|---|---|---|---|---|---|
| ADR-0001 | SDR-0001 | | ADR-0018 | SDR-0011 | | ADR-0029 | SDR-0021 |
| ADR-0002 | SDR-0002 | | ADR-0019 | SDR-0012 | | ADR-0033 | SDR-0022 |
| ADR-0003 | SDR-0003 | | ADR-0020 | SDR-0013 | | ADR-0038 | SDR-0023 |
| ADR-0004 | SDR-0004 | | ADR-0021 | SDR-0014 | | ADR-0039 | SDR-0024 |
| ADR-0005 | SDR-0005 | | ADR-0022 | SDR-0015 | | ADR-0040 | SDR-0025 |
| ADR-0010 | SDR-0006 | | ADR-0023 | SDR-0016 | | ADR-0008 | DEC-0001 |
| ADR-0012 | SDR-0007 | | ADR-0024 | SDR-0017 | | ADR-0009 | DEC-0002 |
| ADR-0014 | SDR-0008 | | ADR-0025 | SDR-0018 | | ADR-0028 | DEC-0003 |
| ADR-0015 | SDR-0009 | | ADR-0026 | SDR-0019 | | ADR-0035 | DEC-0004 |
| ADR-0016 | SDR-0010 | | ADR-0027 | SDR-0020 | | ADR-0036 | DEC-0005 |

Staying as architecture decisions, in `base/decisions/architecture/`: ADR-0006, 0007, 0011, 0013, 0017, 0030, 0031, 0032, 0034, 0037.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| An abstract `Decision`; kinds as local types; a folder, prefix and sequence per kind | The name says what a decision is about; open to product and business decisions without changing the standard; follows the operational kinds | A move of 40 files in this repository and a re-verification of each; old numbers live on in records that cannot be edited | Chosen |
| A built-in catalogue of decision kinds | Every bundle shares the same names | The kinds differ by organization; the standard would guess them before anyone needs them | A kind is added when a bundle needs it, not before |
| One `Decision` type with a kind field, replacing `Architecture Decision` | One type, one folder | Breaks every bundle that has an ADR; a kind cannot carry fields or rules of its own | Breaking, and less than a type |
| Keep `Architecture Decision` for every decision | Nothing to build | 29 of 39 decisions here carry a name that is wrong for them; an operational bundle's decisions have no fitting home | The problem this decision answers |
| One shared sequence and the `ADR-NNNN` name for every kind | Every existing link and citation stays valid; no move | The file name keeps saying ADR for what is not one | The file name is what people cite, so every citation would repeat the wrong name |
| Retype the existing decisions and leave them where they are | No link is rewritten | Two schemes side by side: old decisions named one way, new ones another | A reader would need a decision's date to know what its name means |
| Kinds in subfolders, architecture decisions left in `base/decisions/` | No bundle has anything to move | The folder of one subtype is the parent's folder, so the tree does not mirror the types | Architecture would keep a special place, and the tree would not show which types are decisions |

# Consequences

- Positive: a decision's type and file name say what it is about; a bundle adds a kind of decision in its Domain Profile, with its fields and rules, without waiting for the standard; an operational bundle has a home for decisions that are not architecture; this repository's catalogue shows 25 decisions about the standard, 10 about the plugin and 5 about how it works.
- Negative / accepted debt: 438 lines in 87 files outside `base/decisions/` cite by its number one of the 29 decisions that existed before this one and are renumbered, counted at commit `4687f3b`, among them fragment records, `AGENTS.md`, the logs and the titles of merged pull requests; the records and the git history keep the old numbers, resolved only through the table above and the field of decision 8. Retyping a decision is a content change, so each of the 40 is asked for verification again[^standard]. Existing bundles keep their ADRs in `base/decisions/` until they choose to move them, so two layouts will exist among bundles.
- Follow-up actions (tracker item okf-056, built in layers as [ADR-0009](/base/decisions/DEC-0002-build-in-layers-and-tickets.md) decides): the standard's §4 and the built-in Domain Profile gain `Decision`, the prefix of a type and the former identifier, on top of [ADR-0026](/base/decisions/standard/SDR-0019-built-in-domain-profile.md)[^adr-0026]; a `decision.md` template beside `adr.md`; `okf-capture`, `okf-distill`, `okf-review`, `okf_index.py` and `okf_obsidian.py` read decisions through `Decision`; `okf_lint.py` accepts the prefix each decision type declares in a file name, where today a file named `SDR-0025-decision-types.md` is reported as `NAME_KEBAB`, measured on a copy of this bundle; `okf-migrate` offers the move of `base/decisions/` ADRs to `base/decisions/architecture/`; this bundle's `base/profile.md` declares `Standard Decision`; the 40 decisions are moved with their links rewritten and verified again; `AGENTS.md` and the agents policy name decisions instead of ADRs.

# Related

* [ADR-0008: The okf-builder repo documents its own knowledge with OKF](/base/decisions/DEC-0001-dogfooding.md)
* [ADR-0026: The standard's own types are a built-in Domain Profile](/base/decisions/standard/SDR-0019-built-in-domain-profile.md)
* [ADR-0039: A domain bundle defines its operational kinds and holds their instances next to its layers](/base/decisions/standard/SDR-0024-closing-operational-bundles.md)
* [Domain Profile of okf-builder](/base/profile.md)

[^fragment]: The first fragment: "The question", "The name is wrong, not the shape", "The 39 ADRs sorted by what each decides" and "The owner's conclusion".
[^answers]: The second fragment: the owner's answers "Both" and "Move and renumber all 29".
[^adr-0008]: ADR-0008, description and Decision.
[^adr-0026]: ADR-0026, the built-in Domain Profile declares the standard's types.
[^adr-0039]: ADR-0039, a bundle is a domain bundle or an operational bundle, and the Domain Profile defines each operational kind.
[^standard]: OKF standard, §4 (the `Architecture Decision` row), §2 ("The usual directory of each type (§4) is a default, not a rule") and §6 (content change; a concept edited after a review is asked again).
