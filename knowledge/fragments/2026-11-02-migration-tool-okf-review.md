---
type: Knowledge Fragment
title: "2026-11-02 · What a long-running OKF implementation teaches: open work, drift by nature and profile composition"
description: The owner's reading, with the agent, of a read-only review of a migration tool that has used OKF as profiles-as-data for months, and of a snapshot of its ecosystem with two design meetings, and the decision to revise ADR-0018, ADR-0019 and ADR-0020.
tags: [fragment, standard, profiles, projections, audit]
status: draft
occurred_at: 2026-11-02
origin: Claude Code session in this repository, after a read-only review by two knowledge-architect agents
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: pending
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T05:20:00Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
---

# Record

**What was reviewed.** Two private repositories of the same consulting engagement as the eleven bundles reviewed the day before[^bundles]: a code-migration tool that keeps twelve OKF v0.1 bundles (about 655 typed files) and an OKF plugin with its own validator, and a snapshot of that tool's ecosystem with the transcripts of two design meetings held in mid-October. The meetings describe the design that the newest of the eleven bundles later built: a modular monolith, three lanes and a manifest per module. Both repositories are client material: they are not named or cited, and the detailed reports stayed outside this repository.

**What the tool does with OKF.**

- **The standard and the reading are kept apart.** The upstream spec is copied verbatim with its source commit, hashes and refresh steps; the team's model is called "one reading among others", so another team can share the spec without inheriting the opinion.
- **Profiles are data.** A profile is a Markdown file with a `schema:` map in its frontmatter and a body that justifies each field. Keys: `types`, `required`, `fixed` values, `enums`, `forbidden` keys with a reason, `known`, named `rules` for conditions across fields, `by_type` overrides, `layout: families` (each root folder of a bundle maps to its own schema), `base` and `extends` (an extension may only add), `abstract`, and `validator:` to hand a profile to another tool. A duplicate id across sources is a structural error. Profiles are shared by reference, never copied: "one id is defined once; a copy would diverge".
- **Scope.** One profile is in force per bundle, selected in the bundle's root; variation by folder lives inside it with `layout: families`. Twelve bundles run on nine profiles.
- **Profiles emerge from need, decided by a person.** Fit an existing profile; if one almost fits, propose a new type; if none fits, write a local profile and promote it to the shared catalogue when a second corpus wants it. Friction is raised to a person, "never resolved by relaxing the enum". Each field is justified in the log when the profile is born.
- **Open work is not a fragment.** Meetings produce questions and actions with an owner, what they block, a review date and a default if unanswered. They live in journals whose frontmatter is the present and whose body is an append-only dated record. Each item lives in the one surface of the system that executes or answers it, and every other surface links to it. When an item closes, a tool lists who still cites it as pending.
- **Projections.** Deterministic renders (a bundle rendered as a skill, generated indexes) are checked by regenerating them and comparing, in pre-commit; nothing is recorded after a refresh.
- **Ingestion** keeps a coverage ledger: every source file or section maps to a concept or to "no concept (reason)", so a skipped part cannot pass unnoticed. A contradiction is escalated to a person, never resolved silently.
- **Verification** has a level between proposed and human: "test-backed", verified by a named test. Content that travels outside the team names roles, not people.
- On the tool's bundles, `okf_lint` reports 4 errors and 113 warnings where the tool's own validator reports none: our lint applies our profile to a bundle that declares another.

**What the design meetings add.** The three lanes appear there as "fragments, base, projections"; a fragment is a folder with its material frozen and its SHA-256 recorded, and a repository frozen at a commit is also a fragment; "capturing is not ingesting"; no central registry, because it caused merge conflicts under parallel work, and the inventory is a view computed by a script; the validator warns about a fragment ingested and cited by nobody, or cited and not ingested; "memory holds only decisions and open questions; what is pending lives in the tracker". Projections have a manifest with refs to the base and to other projections, are marked stale when a ref changes and can be frozen.

**Where the ecosystem gave up what okf-builder keeps.** Frontmatter in `index.md` beyond `okf_version`, a local `status` vocabulary that collides with OKF 0.2's, and deleting retired concepts. Each costs lint false positives, a collision with the spec or the lost history of supersessions. The owner keeps okf-builder's stricter choices.

**The owner's decisions.**

1. Revise the three accepted ADRs with new ADRs that supersede them:
   - **ADR-0018**: open questions become concepts in `base/` with an owner; action items go to the team's tracker and are never copied into the base; the fragment only records that they were said.
   - **ADR-0019**: drift depends on a projection's nature: a deterministic projection is checked by regenerating it and comparing; a composed one by `{path, sha256}`.
   - **ADR-0020**: add composition rules (duplicate id as an error, `forbidden` with a reason, `fixed`, `by_type`, named rules, `validator:` delegation), sharing by reference, and a path from a local profile to a shared one.
2. **Scope of a Domain Profile: per bundle, with families.** One profile in force per bundle (`base/profile.md`), with a map from directory to schema inside it, replacing the per-directory inheritance of ADR-0020.
3. **Aliases stay, optional**: a bundle that uses the profile's names declares none.
4. Refinements without an ADR go to the audit and the skills: lint reports spec conformance apart from profile conformance; a hash of a fragment's frozen material and a fragment kind for a repository at a commit; a coverage ledger in `okf-distill`; a reverse index of concepts that cite a target which was then deprecated or closed; the meeting discipline in `okf-fragment` (gaps and attribution in the transcript, the raw transcript never altered, non-professional content left out before freezing, confirmation with someone who was there).
5. Later, apart: a verification level between draft and human, and human actors written as roles in bundles that leave the team; both touch ADR-0005.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| ADR-0018: open questions in `base/`, action items in the tracker | refutation | applied | [ADR-0021](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md) |
| ADR-0019: drift by a projection's nature, and frozen projections | refutation | applied; a third nature, `rendered`, names the deterministic case | [ADR-0022](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md) |
| ADR-0020: one profile per bundle with families, composition rules, sharing by reference, aliases optional | refutation | applied | [ADR-0023](/base/decisions/standard/SDR-0016-domain-profile-per-bundle.md) |
| Refinements for the audit and the skills | addition | pending (okf-1ck) | — |
| Verification level between draft and human; role actors | addition | pending, later (touches ADR-0005) | — |

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
