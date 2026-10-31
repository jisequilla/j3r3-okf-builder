---
type: Architecture Decision
title: "ADR-0012: Knowledge fragments are captured as they happened and distilled into the bundle"
description: A meeting, discussion or transcript is stored as an immutable Fragment concept, and a distillation step proposes the additions, updates and conflicts it brings to the bundle for a person to resolve.
tags: [adr, standard, capture]
status: draft
adr_id: ADR-0012
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T11:45:57Z }
sources:
  - { id: spec-terms, resource: /references/okf-spec-google.md, title: "OKF v0.2 §2 and §3: every .md other than index.md and log.md is a concept" }
  - { id: spec-sources, resource: /references/okf-spec-google.md, title: "OKF v0.2 §5.1: sources may point at bundle paths; lineage is expressed through links" }
  - { id: capture-skill, resource: plugin/okf-builder/skills/okf-capture/SKILL.md }
---

# Context

Knowledge reaches a team as events: a meeting, a design discussion, a review thread, a transcript. Today `okf-capture` turns what a person says into a finished concept in one step[^capture-skill]. The event itself is lost, so a later reader cannot check a claim against what was actually said, and nothing compares the new knowledge with what the bundle already holds. When an event contradicts an existing concept, the contradiction is either missed or silently overwritten.

The OKF spec gives two constraints. Every `.md` file other than `index.md` and `log.md` is a concept, so anything stored as Markdown inside the bundle needs frontmatter[^spec-terms]. A `sources[].resource` may point at a path inside the bundle, and such a link is already an edge of the bundle graph, so a consumer can follow a concept back to what it was derived from[^spec-sources].

# Decision

1. **A fragment is a concept of the new profile type `Fragment`**, stored in `fragments/` as `fragments/YYYY-MM-DD-slug.md`. Its frontmatter carries the usual required fields plus `occurred_at` (when the event happened), `participants` (actors, §7) and `medium` (meeting, chat, document, transcript). Its body holds the record as it happened under `# Record`, edited only to remove secrets and personal data the participants did not agree to keep. A transcript keeps its speaker labels and timestamps, so a reader can tell who said what and find the moment in the recording. A record that already exists elsewhere, such as a meeting transcript in the same tenant, is copied into the fragment, and its original location is kept as the fragment's `sources` entry.
2. **The record is immutable.** After capture only the `# Distillation` section below it changes. A wrong record is deprecated and replaced, never edited.
3. **Distillation is a separate step**, a new skill `okf-distill`, run on one fragment at a time. It reads the fragment and the concepts it touches, then proposes a change set in three groups:
   - *additions*: new concepts, created through `okf-capture`;
   - *updates*: changes to existing concepts that do not contradict them;
   - *conflicts*: statements that contradict an existing concept.
   It applies nothing until a person approves the change set.
4. **Every concept created or updated from a fragment cites it** in `sources` with a bundle path (`resource: /fragments/...`) and footnotes on the claims it supports, so the derivation edge exists in the graph.
5. **A conflict is never resolved by overwriting.** It is listed in the fragment's `# Distillation` section and logged with a new label `**Conflict**`. A person resolves it as one of:
   - the knowledge changed: a decision becomes a new ADR that supersedes the old one, as today; anything else is updated with a `**Update**` entry citing the fragment;
   - a misunderstanding: the conflict is marked rejected in `# Distillation` with the reason, and the concept stays.
6. **Distillation never sets `verified`.** Approving a change set is not reviewing a concept; `verified: human:` stays a separate, explicit act.

The `# Distillation` section lists each proposed item with its outcome (applied, rejected, pending) and a link to the concept it touched, so the fragment shows what it changed.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep capture in one step (today) | Simple | No record of the event, no conflict check | It is the gap this ADR closes |
| Store raw records as non-Markdown files (`references/fragments/*.txt`) | Outside concept tooling; no frontmatter needed | No metadata, not indexed, `okf_lint` cannot check them, `okf-ask` cannot find them | Loses the traceability that motivates fragments |
| Store fragments outside the bundle (a meeting tool, a drive) and cite them by URL | The bundle stays small; sensitive records stay in their own system | Links rot; the bundle cannot be checked or moved as a unit | Kept as an option for sensitive records (see consequences), not the default |
| A separate `Conflict` concept per conflict | Conflicts become searchable, each with its own lifecycle | One more type and directory for something that usually closes within days | The fragment's `# Distillation` section plus the log is enough until conflicts outlive their fragments |
| Distill automatically, without approval | Faster | An agent's reading of a discussion becomes bundle truth unchecked | Contradicts the human-in-the-loop principle of [ADR-0005](/decisions/ADR-0005-required-generated-human-verified.md) |

# Consequences

- Positive: any distilled claim can be traced to the event it came from; contradictions surface as explicit conflicts instead of silent overwrites; meetings and discussions become a regular input to the bundle.
- Negative / accepted debt: the bundle grows with raw records, so `okf-ask` must rank distilled concepts above fragments; records can hold personal or confidential content, so capture must redact, and a record that cannot be published with the bundle stays outside it and is cited by URL; one more profile type, one more directory and one more log label.
- Follow-up actions: once accepted, a layered build ([Build a change in layers](/runbooks/build-in-layers.md)) adding the `Fragment` type and `**Conflict**` label to `OKF-STANDARD.md` (both copies) and `okf_lint`, a `fragment.md` template, the `okf-distill` skill, the `okf-ask` ranking rule and the fragment step in `okf-capture`; check that `okf_migrate` maps the new fields for v0.1 bundles. The fragment format is also the contract with the functional-architect agent.

# Related

* [ADR-0005: generated required and verified only by people](/decisions/ADR-0005-required-generated-human-verified.md)
* [ADR-0007: Single source of skills and per-platform projections](/decisions/ADR-0007-single-source-and-projections.md)
* [OKF spec (Google)](/references/okf-spec-google.md)

[^spec-terms]: OKF v0.2 §2 (Terminology) and §3.1 (Reserved filenames).
[^spec-sources]: OKF v0.2 §5.1 (Provenance) and §6.2 (Path-valued fields).
[^capture-skill]: The `okf-capture` skill, steps 2 to 4.
