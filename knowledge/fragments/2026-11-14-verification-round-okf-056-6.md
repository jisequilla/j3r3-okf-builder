---
type: Knowledge Fragment
title: "2026-11-14 · Verification round okf-056.6 on the review page and three deprecated decisions in a structured question"
description: The owner's 41 stored answers on the private review page, the 39 answerable concepts of round okf-056.6 (the moved decisions and the concepts that cite them) and two concepts outside it, and the three structured questions for the round's deprecated decisions, all confirmed at the version shown.
tags: [fragment, verification]
status: draft
occurred_at: 2026-11-14T17:43:06Z
origin: OKF Review Desk, the owner's private review page (version 11), built 2026-11-14T13:53:53Z from commit 978b11b65d0dab4aa65ea76b7dfeeaf2d34f66db, and a Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "978b11b65d0dab4aa65ea76b7dfeeaf2d34f66db" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T17:44:13Z }
---

# Record

The page showed, as round okf-056.6, the 42 concepts that pull request #122 left with a verification older than their text: the 28 verified decisions among the 41 it moved and the 14 verified concepts whose citations of a renumbered decision it rewrote. Before answering, the owner asked whether an unconfirmed decision could be modified, and proposed changing `make lint` to `just lint` in DEC-0001; the agent answered that a decision's body is not edited and that DEC-0004 records that change, and the owner replied "ok entendido". At the owner's request the page gained an optional comment on a "not confirmed" answer (version 11); no stored answer carries one.

The page's store held these answers, newer than the last applied, each as stored:

| Document | Path | `generated_at` | Choice | `answered_at` | Round |
|---|---|---|---|---|---|
| `base~decisions~DEC-0001-dogfooding.md` (version 2) | /base/decisions/DEC-0001-dogfooding.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:32:26Z | okf-056.6 |
| `base~decisions~DEC-0002-build-in-layers-and-tickets.md` (version 2) | /base/decisions/DEC-0002-build-in-layers-and-tickets.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:36:10Z | okf-056.6 |
| `base~decisions~DEC-0003-where-things-go.md` (version 1) | /base/decisions/DEC-0003-where-things-go.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:54:36Z | okf-056.6 |
| `base~decisions~DEC-0004-just-build-runner.md` (version 1) | /base/decisions/DEC-0004-just-build-runner.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:59:47Z | okf-056.6 |
| `base~decisions~DEC-0005-release-please.md` (version 1) | /base/decisions/DEC-0005-release-please.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:00:21Z | okf-056.6 |
| `base~decisions~architecture~ADR-0007-single-source-and-projections.md` (version 1) | /base/decisions/architecture/ADR-0007-single-source-and-projections.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:00:43Z | okf-056.6 |
| `base~decisions~architecture~ADR-0011-uv-pep723-scripts.md` (version 1) | /base/decisions/architecture/ADR-0011-uv-pep723-scripts.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:00:53Z | okf-056.6 |
| `base~decisions~architecture~ADR-0017-agent-skills-per-platform.md` (version 1) | /base/decisions/architecture/ADR-0017-agent-skills-per-platform.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:01:01Z | okf-056.6 |
| `base~decisions~architecture~ADR-0031-projection-tools-transient-exception.md` (version 1) | /base/decisions/architecture/ADR-0031-projection-tools-transient-exception.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:01:10Z | okf-056.6 |
| `base~decisions~architecture~ADR-0032-obsidian-viewer-setup.md` (version 1) | /base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:01:20Z | okf-056.6 |
| `base~decisions~architecture~ADR-0037-organization-distributed-copy.md` (version 1) | /base/decisions/architecture/ADR-0037-organization-distributed-copy.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:01:31Z | okf-056.6 |
| `base~decisions~standard~SDR-0001-adopt-google-okf.md` (version 1) | /base/decisions/standard/SDR-0001-adopt-google-okf.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:21:54Z | okf-056.6 |
| `base~decisions~standard~SDR-0002-knowledge-folder-per-repo.md` (version 1) | /base/decisions/standard/SDR-0002-knowledge-folder-per-repo.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:22:36Z | okf-056.6 |
| `base~decisions~standard~SDR-0004-dual-support-v01-v02.md` (version 1) | /base/decisions/standard/SDR-0004-dual-support-v01-v02.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:23:15Z | okf-056.6 |
| `base~decisions~standard~SDR-0006-english-canonical-profile-2.md` (version 1) | /base/decisions/standard/SDR-0006-english-canonical-profile-2.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:23:25Z | okf-056.6 |
| `base~decisions~standard~SDR-0008-knowledge-repository-storage.md` (version 1) | /base/decisions/standard/SDR-0008-knowledge-repository-storage.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:24:56Z | okf-056.6 |
| `base~decisions~standard~SDR-0014-three-layers-with-open-questions.md` (version 1) | /base/decisions/standard/SDR-0014-three-layers-with-open-questions.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:25:28Z | okf-056.6 |
| `base~decisions~standard~SDR-0015-knowledge-projections-drift-by-nature.md` (version 1) | /base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:26:24Z | okf-056.6 |
| `base~decisions~standard~SDR-0017-fragment-capture-field-backfill.md` (version 1) | /base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:26:42Z | okf-056.6 |
| `base~decisions~standard~SDR-0019-built-in-domain-profile.md` (version 1) | /base/decisions/standard/SDR-0019-built-in-domain-profile.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:26:55Z | okf-056.6 |
| `base~decisions~standard~SDR-0020-owner-is-a-string-actor-stays-the-spec.md` (version 1) | /base/decisions/standard/SDR-0020-owner-is-a-string-actor-stays-the-spec.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:27:37Z | okf-056.6 |
| `base~decisions~standard~SDR-0021-fragment-material-and-repository.md` (version 1) | /base/decisions/standard/SDR-0021-fragment-material-and-repository.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:27:47Z | okf-056.6 |
| `base~decisions~standard~SDR-0022-verification-recorded-by-question-or-review-page.md` (version 1) | /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:28:06Z | okf-056.6 |
| `base~decisions~standard~SDR-0024-closing-operational-bundles.md` (version 1) | /base/decisions/standard/SDR-0024-closing-operational-bundles.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:28:38Z | okf-056.6 |
| `base~decisions~standard~SDR-0026-decision-types-record-links-and-keys.md` (version 1) | /base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:28:44Z | okf-056.6 |
| `base~doctrine~building-with-agents.md` (version 2) | /base/doctrine/building-with-agents.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:30:26Z | okf-056.6 |
| `base~domain~platform-package.md` (version 2) | /base/domain/platform-package.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:30:47Z | okf-056.6 |
| `base~domain~projection.md` (version 2) | /base/domain/projection.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:31:13Z | okf-056.6 |
| `base~policies~agents-in-this-repo.md` (version 4) | /base/policies/agents-in-this-repo.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:21:34Z | okf-056.6 |
| `base~policies~okf-conformance.md` (version 3) | /base/policies/okf-conformance.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T16:26:32Z | okf-056.6 |
| `base~profile.md` (version 2) | /base/profile.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:32:10Z | okf-056.6 |
| `base~references~okf-compatibility.md` (version 2) | /base/references/okf-compatibility.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:33:56Z | okf-056.6 |
| `base~references~okf-standard.md` (version 2) | /base/references/okf-standard.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:34:05Z | okf-056.6 |
| `base~roles~knowledge-architect.md` (version 2) | /base/roles/knowledge-architect.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:35:30Z | okf-056.6 |
| `base~runbooks~build-in-layers.md` (version 2) | /base/runbooks/build-in-layers.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:38:44Z | okf-056.6 |
| `base~runbooks~export-projections.md` (version 2) | /base/runbooks/export-projections.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:39:45Z | okf-056.6 |
| `base~runbooks~release-version.md` (version 2) | /base/runbooks/release-version.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:40:06Z | okf-056.6 |
| `base~runbooks~update-upstream-spec.md` (version 2) | /base/runbooks/update-upstream-spec.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:40:25Z | okf-056.6 |
| `base~systems~scripts-okf.md` (version 2) | /base/systems/scripts-okf.md | 2026-11-14T13:39:38Z | confirmed | 2026-11-14T17:40:47Z | okf-056.6 |
| `base~domain~attestation.md` (version 1) | /base/domain/attestation.md | 2026-11-13T18:45:12Z | confirmed | 2026-11-14T17:41:38Z | — |
| `base~systems~exporters.md` (version 2) | /base/systems/exporters.md | 2026-11-14T13:13:30Z | confirmed | 2026-11-14T17:41:18Z | — |

Every answer names commit 978b11b65d0dab4aa65ea76b7dfeeaf2d34f66db and page build 2026-11-14T13:53:53Z, and each answer's `generated_at` equals the concept's `generated.at` when applied. Platform package exporters was already verified at this version in a structured question at 2026-11-14T13:20:25Z; the page answer confirms it again.

The page takes no answer on a concept with `status: deprecated`, so the agent asked the round's three deprecated decisions in one structured question, as written here.

> As human:jisequilla, do you verify /base/decisions/architecture/ADR-0034-organization-package.md at commit 978b11b, generated.at 2026-11-14T13:39:38Z? It is deprecated, moved to architecture/ keeping its number; its body is unchanged except link targets.

Options: "Verified" (described as: "I read it in this version and it is correct. Adds a verified entry; its status stays deprecated."), "Not confirmed" (described as: "No verified entry is added; it keeps its VERIFIED_STALE warning. Use the note to say why."). The owner's answer: "Verified".

> As human:jisequilla, do you verify /base/decisions/standard/SDR-0023-domain-and-operational-bundles.md at commit 978b11b, generated.at 2026-11-14T13:39:38Z? It is deprecated, formerly ADR-0038; its body is unchanged except link targets.

Options: "Verified" (described as: "I read it in this version and it is correct. Adds a verified entry; its status stays deprecated."), "Not confirmed" (described as: "No verified entry is added; it keeps its VERIFIED_STALE warning. Use the note to say why."). The owner's answer: "Verified".

> As human:jisequilla, do you verify /base/decisions/standard/SDR-0025-decision-types.md at commit 978b11b, generated.at 2026-11-14T13:39:38Z? It is deprecated, formerly ADR-0040 (superseded by ADR-0041); its body is unchanged except link targets.

Options: "Verified" (described as: "I read it in this version and it is correct. Adds a verified entry; its status stays deprecated."), "Not confirmed" (described as: "No verified entry is added; it keeps its VERIFIED_STALE warning. Use the note to say why."). The owner's answer: "Verified".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| DEC-0001 confirmed | — | verified | [DEC-0001: The okf-builder repo documents its own knowledge with OKF](/base/decisions/DEC-0001-dogfooding.md) |
| DEC-0002 confirmed | — | verified | [DEC-0002: Build multi-stage changes in layers and delegated tickets](/base/decisions/DEC-0002-build-in-layers-and-tickets.md) |
| DEC-0003 confirmed | — | verified | [DEC-0003: Where things go: four homes, workspace tooling as a projection of knowledge, and a Doctrine for how we build](/base/decisions/DEC-0003-where-things-go.md) |
| DEC-0004 confirmed | — | verified | [DEC-0004: The product build runs with just, and its checks are named steps of a build script](/base/decisions/DEC-0004-just-build-runner.md) |
| DEC-0005 confirmed | — | verified | [DEC-0005: Releases are proposed by release-please from squash-merged pull requests with Conventional Commit titles, and a workflow attaches the platform packages](/base/decisions/DEC-0005-release-please.md) |
| ADR-0007 confirmed | — | verified | [ADR-0007: Single source of skills and per-platform projections](/base/decisions/architecture/ADR-0007-single-source-and-projections.md) |
| ADR-0011 confirmed | — | verified | [ADR-0011: Scripts run with uv and declare PyYAML inline (PEP 723)](/base/decisions/architecture/ADR-0011-uv-pep723-scripts.md) |
| ADR-0017 confirmed | — | verified | [ADR-0017: The Claude agent preloads every skill it needs; the Microsoft 365 agent takes a configured subset](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md) |
| ADR-0031 confirmed | — | verified | [ADR-0031: The projection tools are a script and a skill, run a render only on request, never ask a transient projection to be committed, and list recomputable projections for a person](/base/decisions/architecture/ADR-0031-projection-tools-transient-exception.md) |
| ADR-0032 confirmed | — | verified | [ADR-0032: A bundle opens as an Obsidian vault through a viewer setup that a script writes, not a projection](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md) |
| ADR-0037 confirmed | — | verified | [ADR-0037: An organization receives a copy of okf-builder that it owns and versions, pulls later releases when it chooses, and runs lint from the installed plugin](/base/decisions/architecture/ADR-0037-organization-distributed-copy.md) |
| SDR-0001 confirmed | — | verified | [SDR-0001: Adopt Google's Open Knowledge Format as the basis of the standard](/base/decisions/standard/SDR-0001-adopt-google-okf.md) |
| SDR-0002 confirmed | — | verified | [SDR-0002: One bundle per repository in knowledge/](/base/decisions/standard/SDR-0002-knowledge-folder-per-repo.md) |
| SDR-0004 confirmed | — | verified | [SDR-0004: Support OKF v0.1 and v0.2, with v0.2 as the default](/base/decisions/standard/SDR-0004-dual-support-v01-v02.md) |
| SDR-0006 confirmed | — | verified | [SDR-0006: English as the repo's canonical language and profile knowledge/2.0](/base/decisions/standard/SDR-0006-english-canonical-profile-2.md) |
| SDR-0008 confirmed | — | verified | [SDR-0008: A knowledge repository has one source, Git or SharePoint; other tools read it](/base/decisions/standard/SDR-0008-knowledge-repository-storage.md) |
| SDR-0014 confirmed | — | verified | [SDR-0014: A bundle has three layers in profile knowledge/3.0; open questions are concepts in base/ and action items live in the team's tracker](/base/decisions/standard/SDR-0014-three-layers-with-open-questions.md) |
| SDR-0015 confirmed | — | verified | [SDR-0015: Knowledge projections are declared in a projection.yaml, and their drift is checked according to their nature](/base/decisions/standard/SDR-0015-knowledge-projections-drift-by-nature.md) |
| SDR-0017 confirmed | — | verified | [SDR-0017: A fragment's record is immutable, and a missing capture field may be backfilled once from the record itself](/base/decisions/standard/SDR-0017-fragment-capture-field-backfill.md) |
| SDR-0019 confirmed | — | verified | [SDR-0019: The standard's own types are a built-in Domain Profile, the first layer under each bundle's profile, with a level per requirement and typed actors and timestamps](/base/decisions/standard/SDR-0019-built-in-domain-profile.md) |
| SDR-0020 confirmed | — | verified | [SDR-0020: The owner of an operational concept is a string; Actor stays as the OKF spec defines it](/base/decisions/standard/SDR-0020-owner-is-a-string-actor-stays-the-spec.md) |
| SDR-0021 confirmed | — | verified | [SDR-0021: A fragment records its frozen material by SHA-256 and may freeze a repository at a commit, through a map field type](/base/decisions/standard/SDR-0021-fragment-material-and-repository.md) |
| SDR-0022 confirmed | — | verified | [SDR-0022: An agent writes a person's verification only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and version](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md) |
| SDR-0024 confirmed | — | verified | [SDR-0024: A domain bundle defines its operational kinds and holds their instances next to its layers; a closing instance distills into its parent, which keeps the closing fragment, through okf_close.py](/base/decisions/standard/SDR-0024-closing-operational-bundles.md) |
| SDR-0026 confirmed | — | verified | [SDR-0026: A decision is a Decision; Architecture Decision is one kind of it, each kind has its own folder, prefix and sequence, and a link inside a record follows a decision that moves](/base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md) |
| Building with agents confirmed | — | verified | [Building with agents](/base/doctrine/building-with-agents.md) |
| Platform package confirmed | — | verified | [Platform package](/base/domain/platform-package.md) |
| Projection confirmed | — | verified | [Projection](/base/domain/projection.md) |
| Rules for agents working in this repo confirmed | — | verified | [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md) |
| Conformance with profile knowledge/3.0 confirmed | — | verified | [Conformance with profile knowledge/3.0](/base/policies/okf-conformance.md) |
| Domain Profile of okf-builder confirmed | — | verified | [Domain Profile of okf-builder](/base/profile.md) |
| OKF v0.1 ↔ v0.2 compatibility confirmed | — | verified | [OKF v0.1 ↔ v0.2 compatibility](/base/references/okf-compatibility.md) |
| OKF standard, profile knowledge/3.0 confirmed | — | verified | [OKF standard, profile knowledge/3.0](/base/references/okf-standard.md) |
| Knowledge architect confirmed | — | verified | [Knowledge architect](/base/roles/knowledge-architect.md) |
| Build a change in layers confirmed | — | verified | [Build a change in layers](/base/runbooks/build-in-layers.md) |
| Export and deliver platform packages confirmed | — | verified | [Export and deliver platform packages](/base/runbooks/export-projections.md) |
| Publish a plugin version confirmed | — | verified | [Publish a plugin version](/base/runbooks/release-version.md) |
| Update the OKF spec from Google's upstream confirmed | — | verified | [Update the OKF spec from Google's upstream](/base/runbooks/update-upstream-spec.md) |
| OKF scripts confirmed | — | verified | [OKF scripts](/base/systems/scripts-okf.md) |
| Attestation confirmed | — | verified | [Attestation](/base/domain/attestation.md) |
| Platform package exporters confirmed | — | verified | [Platform package exporters](/base/systems/exporters.md) |
| ADR-0034 confirmed | — | verified | [ADR-0034: An organization receives okf-builder as its own package, copied in by a reviewed pull request per release, and each of its repositories pins the version that checks it](/base/decisions/architecture/ADR-0034-organization-package.md) |
| SDR-0023 confirmed | — | verified | [SDR-0023: A domain bundle defines its operational kinds in base and holds their instances as bundles next to its layers, each naming its parent](/base/decisions/standard/SDR-0023-domain-and-operational-bundles.md) |
| SDR-0025 confirmed | — | verified | [SDR-0025: A decision is a Decision; Architecture Decision is one kind of it, and each kind has its own folder, prefix and sequence](/base/decisions/standard/SDR-0025-decision-types.md) |
