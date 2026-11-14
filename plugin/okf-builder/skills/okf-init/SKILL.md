---
name: okf-init
description: Creates the standard knowledge/ structure (OKF v0.2 bundle, knowledge/3.0 profile with the layers fragments/, base/ and projections/) in the current repository. Use when the user says "initialize OKF", "create the knowledge folder", "okf init", "scaffold knowledge", "prepare this repo for OKF", and to set up an existing bundle for reading in Obsidian when the user says "open the knowledge in Obsidian", "set up Obsidian for knowledge/", "okf obsidian". Also opens an operational instance (a request, incident or release) in its kind's directory of a bundle whose Domain Profile declares kinds, when the user says "open a request for…", "new incident", "start release 2.3".
---

# okf-init

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Creates a knowledge/3.0 bundle: `knowledge/` with `index.md` (declaring `okf_version` and `okf_profile: "knowledge/3.0"`), `log.md`, `project.md` and the three layers:

- `fragments/`, with its `index.md`, for the records of events;
- `base/`, with its `index.md` and one typed directory per `--dirs` entry (`base/decisions/`, `base/systems/`...), each with its own `index.md`; `base/decisions/` holds `architecture/`, the directory of the Architecture Decisions, with its own `index.md`;
- `projections/`, with only a `.gitkeep`: it is not OKF, has no `index.md` and the root `index.md` does not list it.

The root `index.md` lists `fragments/` and `base/`; `base/index.md` lists the typed directories. No `conflict-log.md` is created: `okf-distill` creates it with the first conflict. No Domain Profile is created either: the bundle starts under the built-in one alone, and `okf-capture` writes `base/profile.md` from the `domain-profile.md` template when the person asks for one.

No `.okfignore` is created; when `knowledge/` holds paths that are not part of the bundle (drafts, generated files), the person may add one at its root, gitignore-style globs that `okf-lint` does not read (standard §2).

## Steps

1. Find the repo root (where `.git/` or the `CLAUDE.md` is). If `knowledge/index.md` already exists, say so and read its OKF profile, `okf_profile` (missing means knowledge/2.0, the older OKF profile):
   - knowledge/3.0: ask whether to complete the structure (the script is idempotent: it doesn't overwrite without `--force`).
   - knowledge/2.0: do not run the script on it, since it would add `base/` beside the root typed directories and mix the two layouts. Offer the migration instead (`uv run "<skills>/okf-standard/scripts/okf_migrate.py" <root>/knowledge --profile knowledge/3.0 --dry-run`, then without `--dry-run` once the person confirms) and stop.
2. Get the following from the user, or infer it from the repo (README, `package.json`, `pom.xml`, `pyproject.toml`, git remote); ask only for what can't be inferred:
   - `title`: project name.
   - `description`: one sentence.
   - `repo-url`: the git remote, if there is one.
   - `purpose`: what problem the project solves and for whom, if the person or the README says it; without it, Purpose holds the description.
   - `actor`: the user's `human:<id>` (derive it from `git config user.email` before the `@`; confirm).
   - `dirs`: the typed directories under `base/`, all of the OKF profile's by default. If the project clearly has no data or metrics (e.g. a library), propose leaving out `data,metrics,computations`.
3. Run:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_init.py" --root <root> \
     --title "<title>" --description "<description>" --actor <actor> \
     --repo-url "<url>" [--purpose "<purpose>"] [--dirs a,b,c] [--okf-version 0.2|0.1]
   ```
   `--okf-version 0.1` only if the bundle must be consumed by tools that understand only 0.1; 0.2 by default.
4. `knowledge/project.md` holds no placeholder: the script fills the title, description, repository link and Purpose, and leaves out what it cannot fill (Scope, Team and ownership, the other Key links rows), so a fresh bundle has no `SECTION_EMPTY`; its Knowledge map links only the typed directories created. Add a section from the project template (`<skills>/okf-standard/templates/project.md`) only when its content is known from the repo or the person; never write empty rows, placeholders or invented people.
5. Add (or propose adding) to the repo's `CLAUDE.md`:
   ```
   ## Project knowledge
   The knowledge lives in `knowledge/` (OKF v0.2, profile knowledge/3.0): records in `fragments/`, knowledge in `base/`. Start with `knowledge/index.md`.
   To add knowledge use the okf-capture skill; to validate it, okf-lint.
   ```
6. Run `okf-lint` (`uv run "<skills>/okf-standard/scripts/okf_lint.py" <root>/knowledge`) and show the result. `INDEX_EMPTY` warnings in empty directories are expected.
7. Offer the Obsidian viewer setup (ADR-0032): `uv run "<skills>/okf-standard/scripts/okf_obsidian.py" <root>/knowledge` writes `.obsidian/app.json` (Markdown links in relative form, updated on rename), `.obsidian/.gitignore` (git keeps only `app.json` and itself, not each reader's window state) and `knowledge.base` (Bases views: Decisions, Awaiting human review, By type, Going stale over `base/`, Fragments over `fragments/`, reading the fields, values and types the bundle's Domain Profile names through aliases and every type that is a `Decision`, the bundle's local decision types included), so `knowledge/` opens in Obsidian as a vault whose bundle-absolute links resolve. Run it only if the person accepts. It works on an existing bundle too: when the person asks for it on one, run this step alone and skip the others. It never overwrites an existing file without `--force`; show its `created`, `rewritten` and `skipped (exists)` lines.
8. Summarize in 3–5 lines what was created and suggest the first capture (usually `okf-capture` with an ADR or the context architecture view).

## Open a unit of work

A domain bundle whose Domain Profile declares operational kinds under `kinds` (standard §2.2, ADR-0039) works each request, incident or release as an instance: a bundle of its own in its kind's directory, next to the layers. When the person starts one ("open a request for…", "new incident", "start release 2.3"), create it with:

```bash
uv run "<skills>/okf-standard/scripts/okf_init.py" --instance <Kind> --id <id> --in <holder> \
  --title "<title>" --description "<description>" --actor <actor> [--purpose "<purpose>"] [--dirs a,b]
```

- `<Kind>`: an operational kind in force, by its id or a type alias the profile declares for it (written as the id). List them with `uv run "<skills>/okf-standard/scripts/okf_lint.py" <root>/knowledge --profiles`.
- `<holder>`: the bundle that holds the instance: the domain bundle (`<root>/knowledge`), which holds every kind with a directory, or an instance whose kind lists `<Kind>` under `holds` (a request inside a release).
- `<id>`: the instance's directory name, one path segment (`req-42`, `2026-11-incident-db`).
- `--dirs`: the typed directories of the instance's `base/`; none by default, since an instance distills into few.

The script writes `<holder>/<kind directory>/<id>/` with `index.md` (`okf_version`, `okf_profile`, `kind`, `state: open`, `parent: ../..`), `log.md`, `project.md`, `fragments/`, `base/` and `projections/`, then runs okf-index on the instance and on its holder, so the kind's `index.md` lists it. A kind the holder does not hold, an unknown or abstract kind, a holder that is no bundle or is closed or inside a closed instance (frozen, standard §2.2), a holder that is or lies inside a domain bundle declaring `state: closed` (only an operational bundle has a state; `okf-lint` reports that key as `BAD_STATE`, so remove it from the domain bundle's `index.md` first), or an id that is no single directory name (blank, with `/`, `.` or `..`, or naming a file of the kind's directory) exits 2 and writes nothing; say what the message names. Run `okf-lint` on the domain bundle afterwards. Closing an instance is `okf-distill`'s closing mode, not init.

## Don't

- Don't create fictitious example concepts: only the structure and `project.md`.
- Don't add `verified` to anything.
