---
type: Knowledge Fragment
title: 2026-11-15 · The Knowledge Viewer, a page built by a script from any knowledge/ directory
description: The owner's answers to the structured questions of two sessions on the review page that became the Knowledge Viewer, its name, its platform, who confirms what and in which order it is built, and which packages ship it, distilled into ADR-0042.
tags: [fragment, viewer, review, packaging]
status: draft
occurred_at: 2026-11-15T15:44:00Z
origin: Claude Code sessions okf-router-session and okf-worker-session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "4727d0d20edbbd497627565a4bece6a39a1ae252" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T15:46:00Z }
---

# Record

## What the owner said first

Earlier on 2026-11-15, typed by the owner in the router session (free text, context for the questions, not a structured answer):

> the idea is that this could work as a way to present the knowledge owners and they can confirm, the decisions and kownledge concept with a web interface, also navigate the knowledge concepts, it also would be greate to have a visiaul grpaph just us obsidian has to be able to navigate through all the concepts

> the tool should be able to point into a directory ok knowledge, just as we doo with obsidaian and should be able to help us confirm knowlege

## Several owners

Structured question in the router session: "How should several knowledge owners confirm concepts on the review desk?" Options: "One shared page (Recommended)", "One private page per owner", "Single owner for now". The owner's answer: "One shared page (Recommended)".

## Which concepts an owner confirms

Structured question in the router session: "On the review desk, which concepts may a knowledge owner confirm?" Options: "Only their own (Recommended)", "Any concept", "Own by default, any on request". The owner's answer: "Any concept".

## The order of the build

Structured question in the router session: "In what order should the review desk be built?" Options: "Script, apply, graph, owners (Recommended)", "Graph first", "Owners first". The owner's answer: "Script, apply, graph, owners (Recommended)".

## The name

Structured question in the router session: "What should the review desk tool be called in the plugin?" Options: "Review Desk / okf_desk.py (Recommended)", "Knowledge Viewer / okf_viewer.py", "Review Page / okf_review_page.py". The owner's answer: "Knowledge Viewer / okf_viewer.py".

## The platform

Structured question in the router session: "Should the review desk be one self-contained HTML file that reads anywhere and only takes answers when published as a Claude artifact?" Options: "Yes, one file (Recommended)", "Claude artifact only". The owner's answer, typed: "let's start simple for now Claude artifact only, when we need other platforms we decide".

## The tracker

Structured question in the router session: "The bead okf-1lj (knowledge visualizer) is still marked in progress from an old session. How should the board hold this plan?" Options: "okf-1lj becomes the epic (Recommended)", "Close it, new epic". The owner's answer: "okf-1lj becomes the epic (Recommended)".

## Which packages ship it

Structured question in the worker session: "Knowledge Viewer packaging (point 6 of ADR-0042): which packages ship okf_viewer.py and its page template?" Options: "All but Microsoft 365 (Recommended)" (described as: "Ships with the Claude plugin and the link packages (.claude/skills, .agents/skills); the Microsoft 365 package does not ship it, since there is no such page there, as with okf_close.py (SDR-0024 decision 12)."), "Claude packages only" (described as: "Only the Claude plugin and .claude/skills; .agents/skills (Copilot, Gemini) and Microsoft 365 leave it out, since the page is a Claude artifact."), "Every package" (described as: "Ships everywhere okf_init.py ships, Microsoft 365 included, even where the page cannot be published."). The owner's answer: "Claude packages only".

The agent then found that `.claude/skills` and `.agents/skills` are both links to `plugin/okf-builder/skills`, so a file in it cannot be left out of one link alone, and asked again: ".claude/skills and .agents/skills are the same directory (both symlinks to plugin/okf-builder/skills), so okf_viewer.py can't be left out of .agents/skills alone. What should ADR-0042 point 6 say?" Options: "Out of generated non-Claude (Recommended)" (described as: "Ships in the Claude plugin (.plugin) and in the source both links point to; the generated non-Claude packages leave it out: Microsoft 365 (just m365) and the vendorable Copilot pack (just copilot). .agents/skills still sees it, as a link to the source."), "Out of Microsoft 365 only" (described as: "The router's proposal: everything but the Microsoft 365 package ships it, the Copilot pack included."), "Split the links" (described as: "Restructure .agents/skills so it leaves the viewer out; more build work, decided in this ADR and built in layer 1."). The owner's answer: "Out of generated non-Claude (Recommended)".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| What the owner said first | — | context | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| Several owners | — | follow-up, a decision superseding SDR-0022 | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| Which concepts an owner confirms | — | follow-up, with several owners | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| The order of the build | — | tracker, okf-1lj | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| The name | addition | applied | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| The platform | addition | applied | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| The tracker | — | tracker, okf-1lj | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
| Which packages ship it | addition | applied | [ADR-0042](/base/decisions/architecture/ADR-0042-knowledge-viewer.md) |
