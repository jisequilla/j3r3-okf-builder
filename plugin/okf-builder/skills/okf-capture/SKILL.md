---
name: okf-capture
description: Captures a unit of knowledge in knowledge/ using the matching OKF template (ADR, runbook, system, API, table, metric, term, policy, architecture view, reference). Use when the user says "document this decision", "create an ADR", "add a runbook", "register this system", "capture this in knowledge", "okf capture", or when finishing a task has produced knowledge that should persist.
---

# okf-capture

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`.

Turns knowledge (a decision, procedure, component or definition) into an OKF concept that is correctly typed, linked and logged.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop) and **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`). Write in that version.
2. **Classify**: pick the `type` and directory from the `okf-standard` table. If the user doesn't say, infer it from the content and confirm it in one line. Common cases:
   - "we decided to use X instead of Y" → Architecture Decision (`decisions/ADR-NNNN-slug.md`, NNNN = highest existing + 1, 4 digits).
   - "when alert X fires we…" → Runbook.
   - "service X does…, exposes…, depends on…" → System (+ API if there is a contract).
   - "X means…" → Term.
   - "metric X is computed…" → Metric + Attested Computation if there is sanctioned SQL/code.
3. **Read the existing context** before writing: the `index.md` of the target directory and the concepts you will link to (systems, earlier ADRs). Detect duplicates: if an equivalent concept already exists, propose updating it (and, if the decision changes, deprecate it and create the new one with `supersedes`/`superseded_by`).
4. **Write** from the template `<skills>/okf-standard/templates/<type>.md`:
   - Replace every `{{...}}`. `actor` = whoever supplies the content: if the user dictates it and Claude only formats it, `human:<id>`; if Claude synthesizes it from the code/repo, `okf-builder/<model>`. `now` = UTC ISO 8601 `YYYY-MM-DDTHH:MM:SSZ`.
   - Always `status: draft` on creation. Do **not** add `verified`.
   - `description`: one self-contained sentence.
   - Bundle-absolute links (`/systems/x.md`). Link even if the target doesn't exist yet; list the pending links at the end.
   - If the content derives from sources (docs, tickets, URLs, repo files): `sources[]` with `resource` and `id`, and `[^id]` footnotes on the claims that need them. For repo files use repo-relative paths as `resource`.
   - Empty template sections: remove them or leave an explicit `TODO`, never placeholders.
   - **0.1 bundle**: after saving, run `python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <relative-path>` to convert `generated`→`timestamp` and `sources`→`# Citations`; never leave 0.2 keys in a 0.1 bundle.
5. **Log**: add an entry to `knowledge/log.md` under today's date (create the section if it doesn't exist, above the earlier ones): `* **Creation**: ...` / `* **Update**: ...` / `* **Deprecation**: ...`, with a link to the concept. If the directory has its own `log.md`, add it there too.
6. **Index and validate**:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir <directory>
   python3 "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
   python3 "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
   ```
   Fix any ERROR before finishing.
7. **Close**: show the concept's path, its `type` and the pending links, and remind the user that it stays `draft` until a person adds `verified: { by: human:<id>, at: ... }` and moves it to `stable` (offer to do it if the user confirms they have reviewed it: only then use the user's `human:<id>`).

## Batch capture

If the user asks "document the services in this repo" or similar: take an inventory first (list of candidates with type and proposed path), confirm it, then create them one by one following steps 4–6. At most 15 concepts per batch without a new confirmation.
