---
name: okf-index
description: Regenerates the index.md files of knowledge/ from the concepts' frontmatter (grouped by type, with description) and checks whether they are out of date. Use when the user says "regenerate the indexes", "okf index", "update index.md", or after adding/moving/deprecating concepts.
---

# okf-index

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

## Steps

1. Check the state without writing:
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] --check
   ```
2. Regenerate (all, or one directory):
   ```bash
   uv run "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] [--dir <subdir>]
   ```
3. Rules the generator applies (don't duplicate them by hand):
   - Sections by `type` in the profile's order; entries `* [title](file.md) - description`, with a `_(draft)_` / `_(deprecated)_` suffix.
   - A `# Subdirectories` section with the description from the `> ...` blockquote of the child `index.md`, or the profile's.
   - Root: keeps the frontmatter (`okf_version`, `okf_profile`) and any hand-written section starting with `# Notes` (or `# Notas`). In subdirectories it also keeps that section.
4. Show the summarized diff (which indexes changed) and log it in `log.md` only if the change is significant (e.g. a reorganization), not for every routine regeneration.
