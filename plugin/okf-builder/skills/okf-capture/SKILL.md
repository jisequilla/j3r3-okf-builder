---
name: okf-capture
description: Captures a unit of knowledge in knowledge/ using the matching OKF template (ADR, runbook, system, API, table, metric, term, policy, architecture view, reference, open question). Use when the user says "document this decision", "create an ADR", "add a runbook", "register this system", "record this open question", "we don't know X yet", "capture this in knowledge", "okf capture", or when finishing a task has produced knowledge that should persist.
---

# okf-capture

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Turns knowledge (a decision, procedure, component or definition) into an OKF concept that is correctly typed, linked and logged.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop), **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`) and **its profile** (`okf_profile` in the root `index.md`; if missing, knowledge/2.0, the older profile). Write in that version and in that profile's layout.
   - **knowledge/2.0 bundle**: the typed directories sit at the root; drop the `base/` prefix from every directory, bundle path and `--dir` below (`decisions/`, `/decisions/x.md`, `--dir <dir>` then `--dir .`), never mix the two layouts, and offer the migration (`uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --profile knowledge/3.0 --dry-run`, applied only after the person confirms).
2. **Classify**: pick the `type` and directory from the `okf-standard` table. Concepts go under `base/<dir>/`; never write a concept into `projections/` (derived, not OKF) or at the bundle root (only `project.md` and `conflict-log.md` live there). If the user doesn't say, infer it from the content and confirm it in one line. A meeting, transcript or chat to keep as it happened is not a concept: hand it to the `okf-fragment` skill and stop. Common cases:
   - "we decided to use X instead of Y" → Architecture Decision (`base/decisions/ADR-NNNN-slug.md`, NNNN = highest existing + 1, 4 digits).
   - "when alert X fires we…" → Runbook.
   - "service X does…, exposes…, depends on…" → System (+ API if there is a contract).
   - "X means…" → Term.
   - "metric X is computed…" → Metric + Attested Computation if there is sanctioned SQL/code.
   - "we don't know X yet", "who decides Y?" → Open Question (`base/questions/<kebab-slug>.md`, no ID; template `open-question.md`). Ask for its `owner` (the actor who must get it answered, `human:<id>`) and, when it came from a fragment, set `asked_in: /fragments/<file>`; a question raised outside any fragment cites its origin in `sources` and has no `asked_in`. It starts `question_status: open`; add `blocks` (the concepts it holds up) and `review_on` if the person gives them. Before creating it, look in `base/questions/` for the same question still open.
3. **Read the existing context** before writing: the `index.md` of the target directory and the concepts you will link to (systems, earlier ADRs). Detect duplicates: if an equivalent concept already exists, propose updating it (and, if the decision changes, deprecate it and create the new one with `supersedes`/`superseded_by`). If the new knowledge answers an open question in `base/questions/`, the concept cites the question in `sources` (`resource: /base/questions/<slug>.md`), and the question gets `question_status: answered`, `answered_by` with the concept's bundle path, a `# Answer` that summarizes and links it, and a new `generated.at` (its `status` does not change; an **Update** log entry).
4. **Write** from the template `<skills>/okf-standard/templates/<type>.md`:
   - Replace every `{{...}}`. `actor` = whoever supplies the content: if the user dictates it and Claude only formats it, `human:<id>`; if Claude synthesizes it from the code/repo, `okf-builder/<model>`. `now` = UTC ISO 8601 `YYYY-MM-DDTHH:MM:SSZ`.
   - Always `status: draft` on creation. Do **not** add `verified`.
   - `description`: one self-contained sentence.
   - Bundle-absolute links (`/base/systems/x.md`; the templates' example links already use `/base/...`). Link even if the target doesn't exist yet; list the pending links at the end.
   - If the content derives from sources (docs, tickets, URLs, repo files): `sources[]` with `resource` and `id`, and `[^id]` footnotes on the claims that need them. For repo files use repo-relative paths as `resource`.
   - Empty template sections: remove them or leave an explicit `TODO`, never placeholders.
   - **0.1 bundle**: after saving, run `uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <relative-path>` to convert `generated`→`timestamp` and `sources`→`# Citations`; never leave 0.2 keys in a 0.1 bundle.
5. **Log**: add an entry to `knowledge/log.md` under today's date (create the section if it doesn't exist, above the earlier ones): `* **Creation**: ...` / `* **Update**: ...` / `* **Deprecation**: ...`, with a link to the concept. If the directory has its own `log.md`, add it there too.
6. **Index and validate**:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir base/<dir>
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir base
   uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
   uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
   ```
   `--dir base` keeps `base/index.md` listing a new directory. Fix any ERROR before finishing.
7. **Close**: show the concept's path, its `type` and the pending links, and remind the user that it stays `draft` until a person adds `verified: { by: human:<id>, at: ... }` and moves it to `stable` (offer the recorded verification of `okf-review` if the user has reviewed it).

## Batch capture

If the user asks "document the services in this repo" or similar: take an inventory first (list of candidates with type and proposed path), confirm it, then create them one by one following steps 4–6. At most 15 concepts per batch without a new confirmation.
