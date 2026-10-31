---
name: okf-init
description: Creates the standard knowledge/ structure (OKF v0.2 bundle, knowledge/2.0 profile) in the current repository. Use when the user says "initialize OKF", "create the knowledge folder", "okf init", "scaffold knowledge", "prepare this repo for OKF".
---

# okf-init

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Creates `knowledge/` with `index.md`, `log.md`, `project.md` and the profile's subdirectories, each with its own `index.md`.

## Steps

1. Find the repo root (where `.git/` or the `CLAUDE.md` is). If `knowledge/index.md` already exists, say so and ask whether to complete the structure (the script is idempotent: it doesn't overwrite without `--force`).
2. Get the following from the user, or infer it from the repo (README, `package.json`, `pom.xml`, `pyproject.toml`, git remote); ask only for what can't be inferred:
   - `title`: project name.
   - `description`: one sentence.
   - `repo-url`: the git remote, if there is one.
   - `actor`: the user's `human:<id>` (derive it from `git config user.email` before the `@`; confirm).
   - `dirs`: all of the profile's by default. If the project clearly has no data or metrics (e.g. a library), propose leaving out `data,metrics,computations`.
3. Run:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_init.py" --root <root> \
     --title "<title>" --description "<description>" --actor <actor> \
     --repo-url "<url>" [--dirs a,b,c] [--okf-version 0.2|0.1]
   ```
   `--okf-version 0.1` only if the bundle must be consumed by tools that understand only 0.1; 0.2 by default.
4. Fill in `knowledge/project.md`: replace every `{{...}}` placeholder with what is known from the repo (purpose, scope, links). Whatever isn't known, leave as a list with an explicit `TODO`, never unreplaced placeholders.
5. Add (or propose adding) to the repo's `CLAUDE.md`:
   ```
   ## Project knowledge
   The knowledge lives in `knowledge/` (OKF v0.2 format). Start with `knowledge/index.md`.
   To add knowledge use the okf-capture skill; to validate it, okf-lint.
   ```
6. Run `okf-lint` (`uv run "<skills>/okf-standard/scripts/okf_lint.py" <root>/knowledge`) and show the result. `INDEX_EMPTY` warnings in empty directories are expected.
7. Summarize in 3–5 lines what was created and suggest the first capture (usually `okf-capture` with an ADR or the context architecture view).

## Don't

- Don't create fictitious example concepts: only the structure and `project.md`.
- Don't add `verified` to anything.
