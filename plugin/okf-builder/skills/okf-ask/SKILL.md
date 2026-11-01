---
name: okf-ask
description: Answers questions about the project by reading knowledge/ (an OKF bundle) with progressive disclosure, citing concepts, their status and their trust level. Use when the user asks "why did we decide X?", "how do we operate Y?", "what does Z mean in this project?", "what do we know about…?", "check the knowledge", "okf ask", or when a coding task needs architecture or domain context from the repo.
---

# okf-ask

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`.

## Steps

1. Read `knowledge/index.md`. Pick the directories that fit the question (decisions for "why", runbooks for "how to operate", domain for "what does it mean", systems/architecture for "how is it built", data/metrics for "where does this number come from").
2. Read the `index.md` of those directories; select concepts by `description`. Open only the ones you need (at most ~8 in a first pass). Follow links only if the answer requires it. If you need a text search: `grep -ril "<term>" knowledge/`.
3. Assess each concept you use:
   - `status` (`deprecated` ⇒ say so and look for `superseded_by`).
   - `stale_after` in the past ⇒ warn that the content may be stale.
   - Trust: no `verified` ⇒ *unverified*; `verified` with `human:` ⇒ *human-reviewed*; only processes/agents ⇒ *machine-confirmed*.
   - `generated.at` for age; in 0.1 bundles, `timestamp`. Sources: `sources[]` or, in 0.1, the `# Citations` section.
4. Answer directly and briefly. At the end, add a **Sources** block with the path of each concept (`knowledge/decisions/ADR-0007-....md`) and its status/trust on one line. If two concepts contradict each other, say so and prefer the most recent verified one. If a `Knowledge Fragment` and a distilled concept both answer the question, cite the distilled concept first; cite the fragment as the record behind it, never as the established answer.
5. If the knowledge is not in the bundle: say so explicitly, answer with what can be inferred from the code and mark it as *undocumented*, and offer `okf-capture` to record it. If while answering you find an error in a concept, propose the fix (do not apply it without confirmation).

## Don't

- Don't answer from general knowledge of the framework/technology when the bundle holds a project-specific decision: the project's decision wins.
- Don't present `draft` or unverified concepts as established facts without flagging them.
