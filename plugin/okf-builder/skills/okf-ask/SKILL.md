---
name: okf-ask
description: Answers questions about the project by reading knowledge/ (an OKF bundle) with progressive disclosure, citing concepts, their status and their trust level. Use when the user asks "why did we decide X?", "how do we operate Y?", "what does Z mean in this project?", "what do we know about…?", "is X still an open question?", "check the knowledge", "okf ask", or when a coding task needs architecture or domain context from the repo.
---

# okf-ask

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`.

## Steps

1. Read `knowledge/index.md` and its `okf_profile` (missing means knowledge/2.0, the older profile).
   - knowledge/3.0: the root index lists `fragments/` and `base/` (and `projections/` only if it has an `index.md`); read `base/index.md`, which lists the typed directories.
   - knowledge/2.0: the root index lists the typed directories directly. Read the bundle in its own layout; if the person maintains it, mention the migration to knowledge/3.0 with the `okf-migrate` skill.
   Pick the directories that fit the question (decisions for "why", runbooks for "how to operate", domain for "what does it mean", systems/architecture for "how is it built", data/metrics for "where does this number come from"). Do not answer from `projections/`: it is derived from the base for a reader, not OKF knowledge; answer from the base concepts.
2. Read the `index.md` of those directories (`base/<dir>/index.md` in 3.0); select concepts by `description`. Open only the ones you need (at most ~8 in a first pass). Follow links only if the answer requires it. If you need a text search: `grep -ril "<term>" knowledge/base knowledge/fragments knowledge/*.md` (in 2.0, `grep -ril "<term>" knowledge/`).
3. Assess each concept you use:
   - `status` (`deprecated` ⇒ say so and look for `superseded_by`).
   - `stale_after` in the past ⇒ warn that the content may be stale.
   - Trust: no `verified` ⇒ *unverified*; `verified` with `human:` ⇒ *human-reviewed*; only processes/agents ⇒ *machine-confirmed*.
   - `generated.at` for age; in 0.1 bundles, `timestamp`. Sources: `sources[]` or, in 0.1, the `# Citations` section.
   - Open questions: read `base/questions/index.md` (in 2.0, `questions/index.md`) and find the questions that block a concept you use (`grep -rl "<concept bundle path>" knowledge/base/questions`; in 2.0, `knowledge/questions`). If an `Open Question` with `question_status: open` lists a concept you use in its `blocks`, or its title or description matches the question asked, the answer names that question (path) and its `owner` and says the point is still open. A question with `question_status: answered` is followed to its `answered_by` concept, which is the answer; one that is `dropped` is not an answer.
4. Answer directly and briefly. At the end, add a **Sources** block with the path of each concept (`knowledge/base/decisions/ADR-0007-....md`) and its status/trust on one line. If two concepts contradict each other, say so and prefer the most recent verified one. If a `Knowledge Fragment` and a distilled concept both answer the question, cite the distilled concept first; cite the fragment as the record behind it, never as the established answer.
5. If the knowledge is not in the bundle: say so explicitly (if an open question covers it, that is the answer: name it and its owner), answer with what can be inferred from the code and mark it as *undocumented*, and offer `okf-capture` to record it. If while answering you find an error in a concept, propose the fix (do not apply it without confirmation).

## Don't

- Don't answer from general knowledge of the framework/technology when the bundle holds a project-specific decision: the project's decision wins.
- Don't present `draft` or unverified concepts as established facts without flagging them.
