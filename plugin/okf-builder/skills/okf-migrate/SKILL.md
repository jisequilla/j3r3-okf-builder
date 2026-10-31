---
name: okf-migrate
description: 'Migrates an OKF bundle between v0.1 and v0.2 in both directions (timestamp↔generated, # Citations↔sources), detects a bundle''s version and exports downgraded copies for older consumers. Use when the user says "migrate to OKF 0.2", "convert this bundle to 0.1", "which OKF version is this", "okf migrate", "export for a v0.1 consumer", or when okf-lint reports LEGACY_*, V02_FIELD_IN_V01 or MIXED_VERSIONS.'
---

# okf-migrate

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

## Detect the version

```bash
uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle> --no-profile --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['okf_version'],d['version_origin'])"
```
`declared` = `okf_version` in the root `index.md`; `heuristic` = inferred from the fields; `mixed` = 0.1 and 0.2 forms mixed; `default` = no signals (treated as 0.2).

## Migrate

Always `--dry-run` first; show the user the list of affected concepts and the loss notes before writing.

```bash
# 0.1 → 0.2 (lossless). --actor: who to attribute generated.by to for the old concepts
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor> --dry-run
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor>

# 0.2 → 0.1: ALWAYS to a copy (--out); the source bundle stays at 0.2
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --keep-extensions --out <export-dir>

# A single concept (e.g. after okf-capture in a 0.1 bundle with a 0.2 template)
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file runbooks/x.md
```

Choosing `--actor` for 0.1→0.2: if you know who wrote the concepts (e.g. Google's agent), `reference_agent/<model>`; if people wrote them, `human:<id>` only if the user confirms it; when in doubt, `process:okf-migrate` (the default, and honest: nobody knows).

## What is lost when going down to 0.1 (without `--keep-extensions`)

`generated.by`, `verified[]`, `status`, `stale_after`, `usage_window`, and the `sources[]` signals (`author`, `usage_count`, `last_modified`). With `--keep-extensions` they are kept as extra keys: both specs require consumers to tolerate them, but a 0.1 consumer doesn't interpret them. `Attested Computation` becomes a generic type; its computation keys are always kept.

## After migrating

1. `okf-lint` with the target version (`--okf-version 0.2|0.1`) until there are 0 errors.
2. `okf-index` if the `status` change alters the indexes (`_(draft)_` suffixes).
3. The script already adds `okf_version` to the root `index.md` and a `**Migration**` entry to `log.md`; review the text.
4. If `LEGACY_CITATIONS` remain with the note "sources and # Citations differ; Citations section kept as is", resolve them by hand: the section holds citations that aren't in `sources[]`.

## Mapping table

See `<skills>/okf-standard/references/OKF-COMPATIBILITY.md` §2 and §6.
