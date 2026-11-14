---
name: okf-ask
description: Answers questions about the project by reading knowledge/ (an OKF bundle) with progressive disclosure, citing concepts, their status and their trust level. Use when the user asks "why did we decide X?", "how do we operate Y?", "what does Z mean in this project?", "what do we know about…?", "is X still an open question?", "who owns each system?" (a question its Domain Profile maps, answered from the frontmatter with the concepts that lack the field as the gap), "check the knowledge", "okf ask", or when a coding task needs architecture or domain context from the repo.
---

# okf-ask

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`.

## Steps

1. Read `knowledge/index.md` and its OKF profile, `okf_profile` (missing means knowledge/2.0, the older OKF profile).
   - knowledge/3.0: the root index lists `fragments/` and `base/` (and `projections/` only if it has an `index.md`); read `base/index.md`, which lists the typed directories.
   - knowledge/2.0: the root index lists the typed directories directly. Read the bundle in its own layout; if the person maintains it, mention the migration to knowledge/3.0 with the `okf-migrate` skill.
   - **The Domain Profile in force** (knowledge/3.0; a knowledge/2.0 bundle has none): run `uv run "<skills>/okf-standard/scripts/okf_lint.py" knowledge --profiles --json` and read from it, not from `base/profile.md` by hand, the types (with `extends`), the aliases and the `questions` the bundle maps, each with the layer that declared it. **Resolve the aliases when reading** every concept: a local type name is the type it stands for, a field alias the declared field, and a value alias whose `from` holds is its `to`.
   - **A mapped question.** If the question asked is one of `questions` (or plainly the same question), answer it from that mapping first:
     - `concept: /base/...`: that concept is the answer; read it as in step 3 (a missing one is a broken link: say so).
     - `field: Type.field`: `--profiles` gives it with the declared type and field, aliases resolved (`field_as_written` keeps the local names, when the Domain Profile used them). Answer from the frontmatter. The concepts of that type are every concept in `base/` and `fragments/` whose `type`, aliases resolved, is `Type` or a local type that extends it (follow `extends` in `--profiles`). List each one with its value of the field (aliases resolved). **The gap** is each of those concepts without the field, a blank value (empty text, list or map) counting as missing: list it by path, and say how many there are. No concept of that type means the bundle does not answer it yet.
   Pick the directories that fit the question (decisions for "why", runbooks for "how to operate", domain for "what does it mean", systems/architecture for "how is it built", data/metrics for "where does this number come from"). Do not answer from `projections/`: it is derived from the base for a reader, not OKF knowledge; answer from the base concepts.
2. Read the `index.md` of those directories (`base/<dir>/index.md` in 3.0); select concepts by `description`. Open only the ones you need (at most ~8 in a first pass). Follow links only if the answer requires it. If you need a text search: `grep -ril "<term>" knowledge/base knowledge/fragments knowledge/*.md` (in 2.0, `grep -ril "<term>" knowledge/`).
3. Assess each concept you use:
   - `status` (`deprecated` ⇒ say so and look for `superseded_by`).
   - `stale_after` in the past ⇒ warn that the content may be stale.
   - Trust: no `verified` ⇒ *unverified*; `verified` with `human:` ⇒ *human-reviewed*; only processes/agents ⇒ *machine-confirmed*.
   - `generated.at` for age; in 0.1 bundles, `timestamp`. Sources: `sources[]` or, in 0.1, the `# Citations` section.
   - Open questions: read `base/questions/index.md` (in 2.0, `questions/index.md`) and find the questions that block a concept you use (`grep -rl "<concept bundle path>" knowledge/base/questions`; in 2.0, `knowledge/questions`). If an `Open Question` with `question_status: open` lists a concept you use in its `blocks`, or its title or description matches the question asked, the answer names that question (path) and its `owner` and says the point is still open. A question with `question_status: answered` is followed to its `answered_by` concept, which is the answer; one that is `dropped` is not an answer.
4. Answer directly and briefly. At the end, add a **Sources** block with the path of each concept (`knowledge/base/decisions/architecture/ADR-0007-....md`) and its status/trust on one line. If two concepts contradict each other, say so and prefer the most recent verified one. If a `Knowledge Fragment` and a distilled concept both answer the question, cite the distilled concept first; cite the fragment as the record behind it, never as the established answer.
5. If the knowledge is not in the bundle: say so explicitly (if an open question covers it, that is the answer: name it and its owner), answer with what can be inferred from the code and mark it as *undocumented*, and offer `okf-capture` to record it. If while answering you find an error in a concept, propose the fix (do not apply it without confirmation).

## Don't

- Don't answer from general knowledge of the framework/technology when the bundle holds a project-specific decision: the project's decision wins.
- Don't present `draft` or unverified concepts as established facts without flagging them.
