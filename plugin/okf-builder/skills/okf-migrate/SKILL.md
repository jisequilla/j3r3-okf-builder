---
name: okf-migrate
description: 'Migrates an OKF bundle between v0.1 and v0.2 in both directions (timestamp↔generated, # Citations↔sources) and from the older profile knowledge/2.0 to knowledge/3.0 (typed directories under base/), detects a bundle''s version and profile and exports downgraded copies for older consumers. Use when the user says "migrate to OKF 0.2", "convert this bundle to 0.1", "which OKF version is this", "okf migrate", "migrate to knowledge/3.0", "export for a v0.1 consumer", or when okf-lint reports LEGACY_*, V02_FIELD_IN_V01, MIXED_VERSIONS or that the profile is outdated.'
---

# okf-migrate

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

## Detect the version

```bash
uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle> --no-profile --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['okf_version'],d['version_origin'])"
```
`declared` = `okf_version` in the root `index.md`; `heuristic` = inferred from the fields; `mixed` = 0.1 and 0.2 forms mixed; `default` = no signals (treated as 0.2).

The profile is `okf_profile` in the root `index.md`; a bundle without one is knowledge/2.0, the older profile (`okf_lint.py --json` reports it as `"profile_outdated": true`). Version and profile are independent: `--to` never changes `okf_profile` and `--profile` never changes `okf_version`.

## Migrate

Always `--dry-run` first; show the user the list of affected concepts and the loss notes before writing.

```bash
# 0.1 → 0.2 (lossless). --actor: who to attribute generated.by to for the old concepts
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor> --dry-run
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.2 --actor <actor>

# 0.2 → 0.1: ALWAYS to a copy (--out); the source bundle stays at 0.2
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --keep-extensions --out <export-dir>

# A single concept (e.g. after okf-capture in a 0.1 bundle with a 0.2 template)
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file base/runbooks/x.md   # runbooks/x.md in a knowledge/2.0 bundle

# Profile knowledge/2.0 → knowledge/3.0 (okf_version is not changed)
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --profile knowledge/3.0 --dry-run
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --profile knowledge/3.0

# Both at once: the profile step runs first, then the version step walks its result
uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --profile knowledge/3.0 --to 0.2 --actor <actor>
```

At least one of `--to` and `--profile` is required. `--profile knowledge/3.0`:

- **Moves** under `base/` every non-hidden root directory except `fragments/` and `projections/` (the typed directories and any the project added), and every root `.md` other than `index.md`, `log.md`, `project.md` and the Conflict Log.
- **Rewrites** links in every `.md` (reserved files included), `sources[].resource` and the ADR fields `supersedes` / `superseded_by`: a bundle path into a moved path (`/decisions/x.md` → `/base/decisions/x.md`), and a relative path whose target ends up on the other side of the move. Any other path (`/standard/...`, a repo-relative resource) is left as it is.
- **Leaves alone** what `okf-lint` leaves out of the bundle, in both steps: the paths `.okfignore` matches and every nested bundle (an operational instance included) stay where they are, byte-identical, and so does a root directory that holds nothing else but its `index.md` (a kind's directory of instances). A nested bundle is migrated on its own: `okf_migrate.py <its directory>`.
- **Regenerates** the root `index.md`, `base/index.md` and every index below `base/` (`# Notes` kept), sets `okf_profile: "knowledge/3.0"` in the root `index.md` and adds a `**Migration**` entry to `log.md`.

Propose it whenever a skill or `okf-lint` finds a knowledge/2.0 bundle, and run it only after the person confirms; until then, every skill writes in the 2.0 layout.

Choosing `--actor` for 0.1→0.2: if you know who wrote the concepts (e.g. Google's agent), `reference_agent/<model>`; if people wrote them, `human:<id>` only if the user confirms it; when in doubt, `process:okf-migrate` (the default, and honest: nobody knows).

## What is lost when going down to 0.1 (without `--keep-extensions`)

`generated.by`, `verified[]`, `status`, `stale_after`, `usage_window`, and the `sources[]` signals (`author`, `usage_count`, `last_modified`). With `--keep-extensions` they are kept as extra keys: both specs require consumers to tolerate them, but a 0.1 consumer doesn't interpret them. `Attested Computation` becomes a generic type; its computation keys are always kept.

## After migrating

1. `okf-lint` with the target version (`--okf-version 0.2|0.1`) until there are 0 errors; after `--profile`, the profile notice is gone and no `PROFILE_OUTSIDE_LAYER` remains.
2. `okf-index` if the `status` change alters the indexes (`_(draft)_` suffixes).
3. The script already adds `okf_version` (or `okf_profile`) to the root `index.md` and a `**Migration**` entry to `log.md`; review the text.
4. If `LEGACY_CITATIONS` remain with the note "sources and # Citations differ; Citations section kept as is", resolve them by hand: the section holds citations that aren't in `sources[]`.

## Mapping table

See `<skills>/okf-standard/references/OKF-COMPATIBILITY.md` §2 and §6.
