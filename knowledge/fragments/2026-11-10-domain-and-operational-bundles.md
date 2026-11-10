---
type: Knowledge Fragment
title: 2026-11-10 · Domain and operational bundles, with kinds defined in base and instances alongside
description: The owner's structured answers of 2026-11-07 and 2026-11-10, given while designing ticket okf-3vg, on two kinds of bundle, where an operational kind is defined, where its instances live, what their root index declares, how they point to their parent and how a closed one stays frozen; the record that shapes ADR-0038.
tags: [fragment, decision, bundles]
status: draft
occurred_at: 2026-11-10
origin: Claude Code sessions in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "3bd7cea33c9cbfd0a16aa201755073f4e7332c64" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-10T22:34:16Z }
---

# Record

Ticket okf-3vg started from an organization's OKF implementation read on 2026-11-07, where `knowledge/index.md` is a repository manifest over several bundles and a bundle's root index declares `depends_on`. This standard assumes `knowledge/` is one bundle; a nested bundle only gets a notice from lint. The organization's own repositories keep their units of work (a request, an incident, a release and what it ships) as folders with their own fragments, under the rule that what is born in a unit of work stays in its folder. The organization's name is replaced by "[the organization]", as this repository names no organization.

On 2026-11-07, to structured questions:

- Units of work are bundles nested in the domain bundle. The domain bundle holds lasting knowledge and indexes its units of work; each unit is its own small bundle with its own fragments, base, projections, log and Conflict Log, and declares its domain bundle. A closing unit distills what it taught up into the domain bundle; a closed unit is frozen or extracted as its own bundle.
- The pattern is generic, not [the organization]'s: two kinds of bundle, "domain" (knowledge that never closes: a domain, a system, a team, a doctrine) and "operational" (a unit of work that opens, runs and closes: a request, an incident, a release, a project, an engagement, a service migration, a customer case). Organizations name their own operational kinds.
- Operational bundles may hold operational bundles at any depth (a release holds the requests and incidents it ships); each names its parent; lessons are distilled one level up at a time, as a change set a person approves; a closed bundle is frozen (still checked, never edited) or extracted. The same layers at every level. The public ADR uses only generic examples.
- `depends_on` is declarative only: its shape is validated and it is shown, never resolved.

On 2026-11-10 the owner added, in their words:

> Before I answer those questions, we need to bear in mind that the operational bundle needs to be defined as inside of the base bundle as one of it's domainas and how it is worked and structure.

The agent proposed the definition in the domain bundle's `base/` and the instances next to the layers, since instances inside `base/` would put `fragments/` inside `base/` and mix the units' lifecycles into it. The owner answered: "yes, definition in base, instances alongside". Then, to structured questions:

- Where instances live: "Declared per kind": each kind names its directory.
- How lint treats instance bundles: "Recurse by default", with a flag to skip them.
- Whether an instance drops the `lifecycle` field, asked first as "what benefits gives us to drop lifecycle? how do we now if it is a bounded or an open-ended domain, or this comes insided the domain definition?"; after the agent explained that the lifecycle follows from the kind (domain is open-ended, operational is bounded): "Drop it".
- Where a bundle's metadata lives, asked first as "why not use an okf.yaml file? if not i agree each declares it's own on the root index"; after the agent explained that Google's v0.2 spec §12 puts `okf_version` in the root `index.md`, so an `okf.yaml` would state it a second time: "Root index.md", with `okf.yaml` kept for a repository-level manifest.
- How an instance points to where it distills: "parent + depends_on": `parent` required, `depends_on` declarative.
- How a closed bundle is kept frozen: "Convention + review": `closed_at`, and `okf-review` lists concepts changed after it; lint does not read git.
- The repository-level manifest over several domain bundles: "Defer to own bead" (ticket okf-e2k).
- Where the child kinds an operational kind may hold are declared: "On the kind", in the domain bundle's Domain Profile.

Reviewing the draft of ADR-0038, the owner asked, in their words:

> so okay we have the operational bundle in its own folder and it has its own its own fragments, its own log, its own conflict log, and its own knowledge, operational knowledge. knowledge. And I don't think the ADR covers this yet, but when that bundle closes, then all this knowledge should be distilled into the base knowledge to see if there's new conflicts, new changes into the domain. What do you think?

The agent answered that the draft distilled only a closing fragment, which loses what the summary leaves out, and that moving every concept up would flood the domain bundle with what belongs to one unit of work. Then, to structured questions:

- What the closing distillation reads: "Its whole base/": every concept of the instance's `base/` against the parent, each promoted, opened as a conflict or kept in the instance; the approved change set is the closing fragment.
- Whether an instance may close with open conflicts or open questions: "Resolve or carry up": each is resolved or carried up into the parent with a link back; lint errors on a closed instance that still holds one.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Two kinds of bundle, domain and operational, generic | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Kinds defined in the domain bundle's `base/`, instances next to the layers | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Root `index.md` holds `kind`, `state`, `parent`, `depends_on`; no `lifecycle`, no `okf.yaml` | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Nesting, distilling one level up, frozen or extracted | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Closing distills the instance's whole `base/` up; no loose ends at close | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Lint recurses; frozen checked by `okf-review` | addition | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
| Repository-level manifest | — | pending: tracked as a work item (okf-e2k) | tracker |
