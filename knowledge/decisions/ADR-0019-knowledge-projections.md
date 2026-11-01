---
type: Architecture Decision
title: "ADR-0019: Knowledge projections derive from the base for a reader, declared in a projection.yaml and checked for drift by content hash"
description: A projection is a directory in knowledge/projections/ with a projection.yaml (lifecycle, nature, intent, refs with their hashes), its content and its rendered deliverables; it is not OKF and has its own tools, it never regenerates by itself, and this repository's per-platform outputs of the skills are renamed platform packages.
tags: [adr, standard, projections]
status: draft
adr_id: ADR-0019
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:15:00Z }
sources:
  - { id: bundles, resource: /fragments/2026-11-01-real-bundles-review.md, title: "Fragment: what eleven real knowledge bundles teach" }
  - { id: adr-0007, resource: /decisions/ADR-0007-single-source-and-projections.md }
  - { id: adr-0010, resource: /decisions/ADR-0010-english-canonical-profile-2.md }
  - { id: adr-0018, resource: /decisions/ADR-0018-three-layers-fragments-base-projections.md }
---

# Context

[ADR-0018](/decisions/ADR-0018-three-layers-fragments-base-projections.md) gives a bundle a third layer, `projections/`, for what is derived from the base for a reader. In the explored bundles that layer appeared when a deliverable was being edited inside the fragment it came from, which broke the fragment's immutability. Their projections declare a lifecycle, an intent and refs to the base in a `projection.yaml`; a dependency rule keeps a stable projection from depending on a volatile one; a projection is either composed from the base or recomputed by a procedure; and a drift check flags a stale projection without regenerating it[^bundles]. One of their drift checks compared file times, which git does not preserve, and always passed[^bundles].

A projection is not knowledge: it is knowledge arranged for a reader, and a deliverable carries rendered binaries. The owner chose to keep it outside OKF, with its own manifest and its own tools.

In this repository "projection" already names something else: the per-platform outputs of the skills of [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md) (the symlinks, the `.plugin`, the M365 packages, the Copilot pack).

# Decision

1. **A projection is a directory `knowledge/projections/<slug>/`**, with:
   - `projection.yaml`, its manifest;
   - `content.md`, its content;
   - `render/<renderer>.md`, one input per renderer, when it is rendered;
   - `deliverables/`, the rendered files (DOCX, PDF…), latest version only.
2. **`projection.yaml`** declares:

   | Key | Required | Meaning |
   |---|---|---|
   | `lifecycle` | Yes | `canonical` (here to stay; refreshed when its refs change), `deliverable` (versioned and shared outside), `transient` (one-shot; not committed) |
   | `nature` | Yes | `composed` (`content.md` is prose selected from the base) or `recomputable` (`content.md` is the procedure that produces it, and the render holds the dated values) |
   | `intent` | Yes | Audience, scope, tone and what to leave out; it guides every refresh |
   | `refs` | Composed: yes | The base concepts and projections it derives from, each as `{ path, sha256 }`: the bundle path and the hash of its content at the last refresh |
   | `versions` | Deliverable | One entry per delivered version: `version`, `date`, `commit`, and to whom it was sent |

3. **Dependency rule**: a projection may reference the base and projections at least as stable as itself: `canonical` → base and `canonical`; `deliverable` → base, `canonical` and `deliverable`; `transient` → anything. Removing a transient projection can break nothing else.
4. **Drift is measured by content hash.** A projection is stale when a ref's current hash differs from the recorded one. The check lists stale projections and never regenerates them; a refresh proposes the change, a person approves it, and the hashes are recorded again. A recomputable projection with external sources is checked by running its procedure again.
5. **A projection is not OKF.** OKF tools skip `projections/` (ADR-0018). Projection tools own it: a check of `projection.yaml`, the dependency rule and drift, and the steps to create, refresh and render a projection. After a distillation, the projections whose refs changed are listed for refresh.
6. **Vocabulary**: "projection" means a knowledge projection. The per-platform outputs of this repository's skills are **platform packages**: link packages (the symlinks) and generated packages (`make plugin`, `make m365`, `make copilot`). ADR-0007's decision does not change, only its word, so it is not superseded; the same was done for ADR-0010's glossary.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| The manifest in the frontmatter of the projection's `index.md` | Stays inside OKF; no new file type | Treats a derivation as knowledge, and couples projection tools to OKF tools | A projection is not knowledge; its own manifest can grow with its own tools |
| Lifecycle subdirectories (`projections/canonical/<slug>/`, `projections/deliverables/<slug>/`) | Lifecycle visible in the path | Clashes with each projection's `deliverables/`; changing a lifecycle moves the directory | The lifecycle is a key in the manifest |
| Rendered files outside the bundle (`dist/` or a root `/deliverables`) | No binaries in `knowledge/` | The deliverable is separated from the projection it comes from | The owner keeps them with their projection |
| Drift by file time | Nothing to record | Git does not preserve file times; one explored check always passed[^bundles] | Content hashes are deterministic |
| Regenerate stale projections automatically | Always fresh | Rewrites prose nobody asked to change, and diffs land in unrelated commits | A person approves every refresh |

# Consequences

- Positive: deliverables leave the fragments and the base; a projection says what it is for and what it depends on; drift is detectable in CI; the KDD context architect gets a defined hand-off.
- Negative / accepted debt: binaries enter the repository inside `deliverables/`; a projection's quality is not covered by OKF lint; this repository's docs change their word for the platform outputs.
- Follow-up actions: the projection tools (a `projection.yaml` schema, the check and a projection skill), with `okf-distill` listing projections to refresh; the standard says what `projections/` is; rename "projections" to "platform packages" in AGENTS.md, the README, the Makefile messages, `architecture/single-source-projections.md`, `runbooks/export-projections.md`, `systems/exporters.md` and the term `domain/projection.md`.

# Related

* [ADR-0007: Single source of skills and per-platform projections](/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0018: Three layers: fragments, base and projections](/decisions/ADR-0018-three-layers-fragments-base-projections.md)
* [Projection](/domain/projection.md)

[^bundles]: Fragment of 2026-11-01, the review of eleven real knowledge bundles.
