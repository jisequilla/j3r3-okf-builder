---
name: okf-index
description: Regenerates the index.md files of knowledge/ from the concepts' frontmatter (grouped by type, with description) and checks whether they are out of date. Use when the user says "regenerate the indexes", "okf index", "update index.md", or after adding/moving/deprecating concepts.
---

# okf-index

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

## Steps

1. Find the bundle (`knowledge/index.md`, searching upwards from the cwd) and its profile: `okf_profile` in the root `index.md`; if missing, knowledge/2.0, the older profile.
   - knowledge/3.0: the OKF directories are `fragments/`, `base/` and the typed directories under it (`base/decisions`...). `projections/` is skipped: the generator never writes into it, and the root `index.md` lists it only if `projections/index.md` exists.
   - knowledge/2.0: the typed directories sit at the root (`--dir decisions`). Index it in its own layout, never mix the two, and offer the migration to knowledge/3.0 with the `okf-migrate` skill.
2. Check the state without writing:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] --check
   ```
3. Regenerate (all, or one directory):
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] [--dir <subdir>]
   ```
   In a knowledge/3.0 bundle, after adding to a typed directory: `--dir base/<dir>`, then `--dir base` (so `base/index.md` lists a new directory), then `--dir .`.
   To index an operational instance (or any nested bundle), run it on the instance's directory as a bundle of its own: `okf_index.py <bundle>/requests/req-1`; `--dir` into it exits 2.
4. Rules the generator applies (don't duplicate them by hand):
   - Sections by `type` in the profile's order; entries `* [title](file.md) - description`, with a `_(draft)_` / `_(deprecated)_` suffix.
   - A `# Subdirectories` section with the description from the `> ...` blockquote of the child `index.md`, or the profile's.
   - Root: keeps the frontmatter (`okf_version`, `okf_profile`) and any hand-written section starting with `# Notes` (or `# Notas`). In subdirectories it also keeps that section.
   - Skips what lint's scan leaves out, as `okf-lint` does: paths `.okfignore` matches, nested bundles (each operational instance included) and non-OKF directories. It writes no `index.md` there and lists neither ignored paths nor non-OKF directories; a nested bundle stays listed in its parent's `index.md`, and a kind directory that holds only instances keeps its own.
5. Show the summarized diff (which indexes changed) and log it in `log.md` only if the change is significant (e.g. a reorganization), not for every routine regeneration.
