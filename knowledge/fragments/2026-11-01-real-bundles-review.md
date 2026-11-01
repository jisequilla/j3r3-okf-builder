---
type: Knowledge Fragment
title: "2026-11-01 · What eleven real knowledge bundles teach: three layers, projections and a taxonomy per domain"
description: The owner's reading, with the agent, of a read-only exploration of eleven private knowledge bundles from one consulting engagement, and the patterns to adopt in the standard (three layers, projections, domain taxonomy in each index.md) and to leave out.
tags: [fragment, standard, projections, taxonomy, audit]
status: draft
occurred_at: 2026-11-01
origin: Claude Code session in this repository, after a read-only exploration by five knowledge-architect agents
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: pending
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T21:20:00Z }
---

# Record

**What was explored.** Eleven knowledge bundles kept in private repositories of one consulting engagement, read without changes by five knowledge-architect agents. The bundles, their systems and their people are client material: they are not named or cited here, and the detailed reports stayed outside this repository.

**How the bundles evolved.** They are not eleven independent designs but one design over about seven months:

1. **Two layers.** `fragments/` holds what was said, immutable and dated; `base/` holds what the team knows, organised by domain and written in the present tense. The motto is "knowledge over documentation": the base is raw material to generate the right answer for the right reader, not a polished document. Metadata lives in a central `registry.yaml`, and concepts have no frontmatter.
2. **Projections as a third layer.** A deliverable was being edited inside the fragment it came from, which broke the fragment's immutability. Derived artefacts got their own layer, `projections/`, each with a `projection.yaml`: a `lifecycle` (`canonical`, here to stay and regenerated when its sources change; `deliverable`, a versioned artefact shared outside; `transient`, one-shot and not kept), an `intent` (audience, scope, what to leave out) and `refs` to the base. A dependency rule lets a projection reference only the base and projections at least as stable as itself, so removing a transient one cannot break a canonical one. A drift check flags a stale projection and never regenerates it by itself. A later decision added a projection's nature: *composed* (prose selected from the base) or *recomputable* (its content is a procedure to run again, and the render holds the dated values).
3. **OKF on the surface only.** OKF was then adopted "as a convention, not a dependency", first only for projections that machines consume. Ideas from that stage: the frontmatter is the axis of completeness (a missing field is the gap); a profile emerges from need and is justified field by field in `log.md`; OKF says what exists and a skill says how to operate.
4. **OKF everywhere, with a taxonomy per module.** The latest bundles use OKF for the whole repository. A root manifest holds the exclusions, the modules in reading order and the origins of fragments with the recipe that ingests each. Each module declares its types (each may extend a common type), their typed fields (type, required, note), the questions it answers (each mapped to a field or a concept), its dependencies on other modules and the common types it uses. Their validator knows no type by name: it reads the taxonomy from the declarations. A new type appears only when three notes share a shape. The three layers survive inside OKF in one of them.

**What the exploration measured.** On these bundles, `okf_lint` reports 60 to 98% false positives, because it has no exclusion list, cannot tell a non-OKF or nested bundle and assumes version 0.2. The real gaps it misses: fragments marked distilled that no concept cites, or cited and still pending; months-old pending fragments; sources declared and never footnoted; concepts edited after a person verified them (59 of 68 in one bundle); concepts deleted or renamed without deprecation; person verifications without `human:`; dozens of `stale_after` dates falling in the same ten days; and committed credentials, which no okf-builder check looks for. None of the bundles keeps a Conflict Log; they carry uncertainty as open-question concepts with an owner.

**The owner's reading and decisions.**

- The patterns to adopt are the three layers, projections and a different taxonomy for each domain as an extension of the OKF frontmatter.
- **Projections**: adopt the manifest (`lifecycle`, `intent`, `refs`), the dependency rule, the composed and recomputable natures and a drift check that never regenerates by itself. Drift compares content hashes, not file times, which git does not preserve; one of the bundles found its time-based check always passed.
- **Base**: adopt the layer rule, not a `base/` directory. The profile's typed directories already are the knowledge layer, and renaming them would break every bundle for no gain. Also adopt the list of what stays in fragments (logistics, action items, tone, commercial terms, unvalidated proposals), current-state prose without dated history mixed in, and a size guide per concept.
- **Domain taxonomy**: a domain declares its types, fields and questions as data, and lint and the skills read the declaration instead of a fixed list; an alias map lets `okf-distill`, `okf-review` and `okf-ask` recognise local names for the profile's types and fields. The declaration lives in the frontmatter of the domain directory's `index.md`, not in a separate manifest file: it stays inside OKF and adds no file type.
- **Not adopted**: a central registry instead of frontmatter (it is where most of the drift was, and the latest bundles moved state back into frontmatter); deleting concepts; hand-written `README.md` indexes; binaries inside the bundle.
- **Name clash**: in this repository "projections" names the per-platform exports of the skills. The knowledge layer takes the name, which KDD and every explored bundle use, and the exports are renamed.
- **Order**: two ADRs, three layers with projections (including the rename) and domain profiles; then the audit (lint checks and an audit mode in `okf-review`), so it checks against the declared taxonomy.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
