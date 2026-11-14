---
type: Knowledge Fragment
title: 2026-11-13 · Not every decision is an Architecture Decision, and how the standard and this repo should type decisions
description: The owner asked whether every decision is an ADR; the agent sorted this bundle's 39 ADRs by what each decides (24 about the standard, 10 about the plugin, 5 about how the repo works), and the owner chose an abstract Decision type in the standard, a local Standard Decision here, a folder, prefix and sequence per kind, and retyping the 29 non-architecture ADRs, filed as okf-056.
tags: [fragment, okf, decisions, adr, domain-profile, types]
status: draft
occurred_at: 2026-11-13T19:17:33Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "4687f3b2894769cdd0dc062114745ca35359239a" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-13T19:17:33Z }
sources:
  - { id: adr-0028, resource: /base/decisions/DEC-0003-where-things-go.md, title: "ADR-0028: Where things go" }
  - { id: standard, resource: plugin/okf-builder/skills/okf-standard/references/OKF-STANDARD.md, title: "OKF standard, §2 (domain and operational bundles), §4 (type vocabulary) and §6 (lifecycle)" }
  - { id: obsidian-script, resource: plugin/okf-builder/skills/okf-standard/scripts/okf_obsidian.py, title: "okf_obsidian.py, the test that declares Product ADR as a local type extending Architecture Decision" }
---

# Record

## The question

The owner asked, in their words:

> ok so the other day i had a discussion with a friend about decissions, currently our decissions are ADR, but are all decissions really ADR?

The friend took no part in this session; what they said is known only through the owner's words below.

The agent read the type vocabulary of the standard, the list of this bundle's decisions and ADR-0028, and answered no, for two reasons taken from the bundle itself:

- Decisions that are not ADRs already live elsewhere in the bundle: a conflict resolution is a row of the Conflict Log with a "who decided" column; an audit finding accepted as is is a `log.md` entry; an approved change set is kept in a fragment's ledger[^standard]. ADR-0028 created the Doctrine type because "ADRs cannot hold such practice, because history is never edited"[^adr-0028]; a Policy holds rules and an Open Question what is not yet decided.
- Many of the 39 ADRs are not architecture. From the titles alone the agent estimated about eight (ADR-0003, 0008, 0009, 0025, 0033, 0032, 0035, 0036), an estimate it corrected later in the session.

The agent split the question in two: whether a decision deserves a record at all (the ADR shape, with context, alternatives, consequences and supersession instead of editing, earns its cost when the decision is expensive to reverse, had real alternatives and someone will later ask why), and whether the record is "architecture". It said the shape is general and the adjective is the narrow part, and that the gap matters more for OKF than for a software repository, because the standard now covers domain bundles and operational bundles such as requests, incidents and engagements[^standard], where a team recording "the committee approved the exception" has no home for it except a type called `Architecture Decision` with an `adr_id`.

The agent said, from memory and not checked in the session, that MADR renamed itself to "Markdown Any Decision Records" for this reason.

The agent asked what the friend's claim was: that some decisions need a different shape, or that the name is wrong.

## The name is wrong, not the shape

The owner answered:

> the name is wrong, not the shape, i mean there are diffrent type of decissions and maybe we should try to model this, since Architecture Decissions are for the architecture and other decissions should be cattalog as such, what do you think=

The agent agreed with modelling it and argued against a catalogue of decision kinds in the standard. Its proposal: an abstract built-in type `Decision`, which `Architecture Decision` extends; every other kind is a local type a bundle declares in its Domain Profile, extending `Decision`. Its reasons:

- Today the only way to model a non-architecture decision is a local type that extends `Architecture Decision`; a test in `okf_obsidian.py` declares `Product ADR` that way[^obsidian-script]. That says a product decision is a kind of architecture decision.
- The standard already does this for operational bundles: it ships only the abstract kind `Operational Bundle`, and "which kinds of work exist is the organization's to name"[^standard].
- `Architecture Decision` would keep its name, fields and directory, and the behaviours of an ADR (a body never edited, supersession, the Obsidian Decisions view) would attach to `Decision` and reach what extends it. The agent said it had not traced every script, so this was a design expectation.

The agent added that a separate type earns its place only when the kinds differ in fields, rules or who decides, that a tag does the same otherwise, and that a doubtful case should default to plain `Decision`. It named two open points: identity (`adr_id` and the `ADR-NNNN` file prefix are tied to the architecture type) and what happens to this repo's existing ADRs.

Structured question, "How should the OKF standard model decisions that are not architecture decisions?", with the options:

1. Abstract `Decision` (recommended): a new built-in type `Decision`; `Architecture Decision` extends it and keeps its name and fields; other kinds are local types each bundle declares in its Domain Profile.
2. Built-in catalogue: the standard ships a fixed set of decision types next to `Architecture Decision`.
3. One `Decision` with a kind field: rename `Architecture Decision` to `Decision` and add a field such as `decision_kind`; a breaking change for existing bundles.

The owner's answer: "Abstract `Decision` (Recommended)".

Structured question, "What should I do with this now?", with the options: record an Open Question (recommended), draft the ADR, keep discussing. The owner's answer: "Keep discussing".

## The 39 ADRs sorted by what each decides

The agent read the title, description and `decision_status` of each of the 39 ADRs at the commit this fragment names, not their bodies, and sorted them:

| What the decision is about | Count | ADRs |
|---|---|---|
| The standard itself: format, layers, types, fields, rules a bundle must follow | 24 | 0001, 0002, 0003, 0004, 0005, 0010, 0012, 0014, 0015, 0016, 0018, 0019, 0020, 0021, 0022, 0023, 0024, 0025, 0026, 0027, 0029, 0033, 0038, 0039 |
| How the plugin is built and shipped: scripts, skills, agents, packages | 10 | 0006, 0007, 0011, 0013, 0017, 0030, 0031, 0032, 0034, 0037 |
| How the repo works: build runner, releases, tickets, dogfooding, where files go | 5 | 0008, 0009, 0028, 0035, 0036 |

The agent corrected its earlier estimate: ADR-0003, 0025, 0032 and 0033 are standard or tooling decisions, so five are about process, not about eight. Its reading of the table:

- The largest group is not software architecture: only the ten plugin decisions are architecture in the classic sense.
- The kinds found are specific to this repository; another team would have product, commercial or governance decisions, which supports the abstract `Decision` with kinds declared per bundle.
- A decision about the standard has consequences the other two kinds do not: the standard's text, the compatibility matrix and lint must change, and it may break bundles that passed lint. That could be a field of its own.
- Three records span two kinds: ADR-0010 (repo language and profile vocabulary), ADR-0028 (file layout and doctrine) and ADR-0008. A record that fits no single kind needs a default home, plain `Decision`.

The agent proposed three types for this repository: `Architecture Decision` for the plugin, a local `Standard Decision`, and plain `Decision` for the five process decisions.

## The owner's conclusion

The owner answered:

> this explains perfectly the conclussion we had, that not all decisions are ADR, and here also makes more sense, specially since we are extending the okf standard and building something meta, so i agree with this three types for our case, i would add any other type of decissions now, until we need it, since we should adopt YAGNI principle and KISS, and keep the standard open so this can be extended to product or business decission when needed.

The agent read "i would add any other type of decissions now, until we need it" as "I would not add any other type now", said so, and the owner did not correct it.

The agent stated the scope: in the standard, one new abstract built-in type `Decision` that `Architecture Decision` extends, with no catalogue of kinds; in this repo's Domain Profile, one local type `Standard Decision` extending `Decision`, the five process decisions being plain `Decision`. It said the change needs a new ADR, and that under the standard a change of a concept's `type` is a content change and a concept edited after a person verified it is asked again[^standard], so retyping the 29 non-architecture ADRs means up to 29 re-verifications.

Structured question, "We agreed on an abstract `Decision` type in the OKF standard plus a local `Standard Decision` in this repo. How should I record it?", with the options: draft ADR-0040 as proposed (recommended), record an Open Question, capture the discussion as a fragment first. The owner's answer: "Capture the discussion as a fragment first".

Structured question, "How should decisions that are not architecture decisions be identified and named in files?", with the options:

1. One sequence, keep `ADR-NNNN` (recommended): every kind keeps the `ADR-NNNN-slug.md` file name and one shared numbering.
2. One sequence, new prefix for new kinds: architecture decisions stay `ADR-NNNN`; other kinds use a neutral prefix such as `DEC-NNNN`, continuing the same numbering.
3. A prefix and sequence per kind, for example `ADR-0011`, `SDR-0001`, `DEC-0001`.

The owner's answer, written in their own words instead of an option:

> i think each kind should have it's own folder and it's own prefix and sequeence and it should be define in the decission card and or template.

Structured question, "What should happen to the 39 existing ADRs, 29 of which are not architecture decisions (24 about the standard, 5 about how the repo works)?", with the options: leave them and type new ones (recommended), retype all 29, retype only the accepted ones. The owner's answer: "Retype all 29".

While the agent was capturing this fragment the owner added:

> specially thinkng in an operational bundle there not all decissions are ADR

## What was left open

- What "the decission card" names in the owner's answer on identity: the agent read it as the declaration of the decision type (where a kind's folder, prefix and sequence would be declared, as an operational kind declares its `directory`), and had not asked the owner when this fragment was captured.
- Whether renaming the files of the 29 retyped ADRs to a new prefix and moving them to a new folder is part of "Retype all 29": the question offered a change of `type` with bodies untouched, and the owner's answer on identity (a folder, prefix and sequence per kind) was given in the same round.
- The claim about MADR's name was not checked.
- The agent filed the work as okf-056 in the tracker.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The question | Addition | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |
| The question | — | context | no concept (the claim about MADR's name was not checked) |
| The name is wrong, not the shape | Addition | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |
| The 39 ADRs sorted by what each decides | Addition | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |
| The owner's conclusion | Addition | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |
| What was left open | Addition | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |
| What was left open | — | not distilled | tracker |

[^adr-0028]: ADR-0028, Context, second paragraph.
[^standard]: OKF standard, §2 (a bundle is a domain bundle or an operational bundle; the standard ships only the abstract kind `Operational Bundle`), §4 (the `Architecture Decision`, `Conflict Log` and `Knowledge Fragment` rows) and §6 (content change and human review; the audit's findings accepted as is).
[^obsidian-script]: okf_obsidian.py, the test profile `types: Product ADR: extends: Architecture Decision`.
