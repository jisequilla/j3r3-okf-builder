---
type: Knowledge Fragment
title: "2026-11-13 · Splitting the decision-types build into layers: links inside fragment records and the names of the new keys"
description: Asked to split okf-056 into layer tickets, the agent measured the build against the repository, found that 10 links inside 6 fragment records would break under ADR-0040 decision 7, and the owner chose to rewrite only their targets and the key names prefix, decision_id and formerly.
tags: [fragment, okf, decisions, adr, layers, tickets]
status: draft
occurred_at: 2026-11-13T20:19:44Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "acdb5ed1135b35ffa0fecb8c13db341c81845b2b" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-13T20:19:44Z }
sources:
  - { id: adr-0040, resource: /base/decisions/standard/SDR-0025-decision-types.md, title: "ADR-0040: A decision is a Decision" }
---

# Record

## The request and the measurements

The owner wrote:

> split okf-056 into layer tickets

The agent read the runbook Build a change in layers and measured the build against the repository at the commit this fragment names:

- `KEBAB_RE` in `okf_common.py` accepts a file name with the prefix `ADR-NNNN-` and no other prefix, so lint reports a file named `SDR-0025-decision-types.md` as `NAME_KEBAB`.
- The types of both profiles already declare a `directory`; `okf_profile.py` accepts the type keys `extends`, `description`, `fields`, `directory` and `note`.
- `okf_index.py` wrote an index for a subfolder of `base/decisions/` and listed it under `# Subdirectories` in the parent's index, on a scratch copy of the bundle.
- Three pull requests of okf-3vg are open (#109, #110, #111) and edit `okf_init.py`, `okf_index.py`, `okf_migrate.py`, `okf_lint.py`, `okf_close.py` and the standard's text.
- Outside `base/decisions/` and `fragments/`, 163 links and `sources` entries in `knowledge/` point to a decision file; inside `base/decisions/`, 229.
- 6 of the 26 fragments hold 10 links to decision files inside their `# Record`. ADR-0040 decision 7 says links inside a record are not rewritten[^adr-0040], so after the move those links would point nowhere and lint would report them. The migration from knowledge/2.0 to 3.0 rewrote the targets of links inside fragments.

## The proposed layers

The agent proposed: layer 1, the standard, the built-in profile, `okf_profile.py`, a `decision.md` template and the root copies; layer 2, three tickets in parallel (lint; index, Obsidian and init; migrate); layer 3, the skills' text, the knowledge-architect agent and the example bundle and fixtures; layer 4, two tickets (this bundle's profile and the move of the 40 decisions with the links in `knowledge/`; the citations by number in `AGENTS.md`, the agents policy, the README, the workflows and the plugin's text), followed by the owner's re-verification.

The agent said what it had settled for the tickets' text: the build starts after pull requests #109, #110 and #111 merge; retyping and renumbering this repository's decisions is done by a script that is not shipped, and only the move of decisions to the folder their type declares goes into `okf-migrate`; the example bundle moves to the new layout; no bundle that passes lint is expected to fail it, so the tickets are `feat:` without `!`.

## The owner's answers

Structured question, "After the 40 decisions move, 10 links inside 6 immutable fragment records will be broken, because ADR-0040 decision 7 says links inside a record are not rewritten. How should that be handled?", with the options:

1. Rewrite the target only (recommended): in a record, only the path inside the link changes; the visible text stays as it was said; this is what the 2.0 to 3.0 migration did; it changes one clause of ADR-0040, so a short new decision supersedes that clause before the build.
2. Lint ignores links in records: records stay byte-for-byte as captured and lint stops checking links inside a fragment's `# Record`.
3. Leave them broken: keep ADR-0040 as written; lint reports the 10 links on every run.

The owner's answer: "Rewrite the target only (Recommended)".

Structured question, "ADR-0040 says each decision type declares its prefix and each moved decision records its former identifier, but names neither key. Which names should the tickets use?", with the options:

1. `prefix`, `decision_id`, `formerly` (recommended): a generic id on `Decision`; `Architecture Decision` keeps `adr_id` as its own name for it, so existing bundles need no change.
2. `prefix`, `decision_id` everywhere: `adr_id` is deprecated in favour of `decision_id` and existing bundles are migrated.
3. `id_prefix`, `decision_id`, `former_id`: the first option with longer key names.

The owner's answer: "prefix, decision_id, formerly (Recommended)", with the preview:

```yaml
# built-in profile
Decision:
  directory: /base/decisions/
  prefix: DEC
  fields:
    decision_id: { type: string }
    formerly:    { type: string }
Architecture Decision:
  extends: Decision
  directory: /base/decisions/architecture/
  prefix: ADR          # adr_id stays

# a moved decision
type: Standard Decision
decision_id: SDR-0022
formerly: ADR-0033
```

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The request and the measurements | Addition | applied | [ADR-0041](/base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md) |
| The proposed layers | — | not distilled | tracker |
| The owner's answers | Addition | applied | [ADR-0041](/base/decisions/standard/SDR-0026-decision-types-record-links-and-keys.md) |
| The owner's answers | Refutation | applied | [ADR-0040](/base/decisions/standard/SDR-0025-decision-types.md) |

[^adr-0040]: ADR-0040, decision 7, last sentence.
