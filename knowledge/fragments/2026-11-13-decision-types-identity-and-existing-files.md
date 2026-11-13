---
type: Knowledge Fragment
title: 2026-11-13 · Decision types, the owner's answers on where a kind's folder and prefix are declared and on moving the 29 existing ADRs
description: After the fragment on decision types was captured, the owner answered the two points it left open, that a kind's folder, prefix and sequence are declared both in the type's declaration and in its template and that the 29 non-architecture ADRs move and are renumbered, and chose to distill before opening one pull request.
tags: [fragment, okf, decisions, adr, domain-profile, types]
status: draft
occurred_at: 2026-11-13
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-13T19:26:09Z }
sources:
  - { id: first, resource: /fragments/2026-11-13-decision-types-beyond-adr.md, title: "2026-11-13 · Not every decision is an Architecture Decision, and how the standard and this repo should type decisions" }
---

# Record

This continues [the fragment on decision types](/fragments/2026-11-13-decision-types-beyond-adr.md) of the same session, whose record was already frozen and left two points open[^first].

Structured question, "You wrote that each decision kind's folder, prefix and sequence 'should be define in the decission card and or template'. What does 'decision card' name?", with the options:

1. The type's declaration in the profile: each decision type declares its folder and prefix where the type is defined, the built-in profile for `Decision` and `Architecture Decision` and the bundle's `base/profile.md` for local kinds such as `Standard Decision`; lint and okf-capture read it from there.
2. The decision concept itself: each decision file carries its kind's id in its own frontmatter, as `adr_id` does today, and the template of each kind fixes the prefix and folder; nothing new in the profile.
3. Both: the profile declares the folder and prefix per type, and each kind also has its own template whose frontmatter and file name follow that declaration.

The owner's answer: "Both".

Structured question, "You chose to retype all 29 non-architecture ADRs and also a folder, prefix and sequence per kind. Do the 29 existing files move and get renamed too?", with the options:

1. Retype only, keep `ADR-NNNN` names (recommended): the 29 change `type` and stay in `base/decisions/` under their names, so every existing link and citation stays valid; new folders, prefixes and sequences apply to decisions written from now on.
2. Move and renumber all 29: each of the 29 moves to its kind's folder with a new prefix and number (for example the 24 standard decisions become SDR-0001…0024), and every link and citation to them is rewritten.
3. Move, keep the old numbers: the 29 move to their kind's folder and take the new prefix but keep their number (for example ADR-0033 becomes SDR-0033).

The owner's answer: "Move and renumber all 29".

Structured question, "The fragment, its log entry and the regenerated fragments index are uncommitted on main. What next?", with the options: new branch and PR (recommended), distill first then one PR, leave uncommitted. The owner's answer: "Distill first, then one PR".

The prefixes `SDR` and `DEC` appear in the questions only as examples; the owner was not asked to choose a prefix or a folder name for any kind.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The question on what "decision card" names | Addition | applied | [ADR-0040](/base/decisions/ADR-0040-decision-types.md) |
| The question on whether the 29 existing files move | Addition | applied | [ADR-0040](/base/decisions/ADR-0040-decision-types.md) |
| The question on the uncommitted files | — | context | no concept (logistics of this session) |
| The prefixes named only as examples | Addition | applied | [ADR-0040](/base/decisions/ADR-0040-decision-types.md) |

[^first]: The first fragment, section "What was left open".
