---
type: System
title: OKF scripts
description: okf_init, okf_lint, okf_profile, okf_index, okf_migrate, okf_audit, okf_projection and okf_obsidian (Python ≥ 3.9 and PyYAML, run with uv) in okf-standard/scripts.
resource: /plugin/okf-builder/skills/okf-standard/scripts
tags: [system, scripts, python]
status: draft
owner: human:jisequilla
runtime: uv
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-11T22:27:29Z }
verified: { by: human:jisequilla, at: 2026-11-09T10:56:54Z }
---

# Responsibility

| Script | Function | Output |
|---|---|---|
| okf_init.py | Scaffold of `knowledge/` (v0.2 or v0.1) | files; regenerates indexes |
| okf_lint.py | Spec conformance (§11) + profile; version detection | ERROR/WARN findings, `--json`, exit code |
| okf_profile.py | Loads and composes a knowledge/3.0 bundle's Domain Profile (built-in, `extends`, `base/profile.md`); `--check-builtin` checks the built-in profile against the standard's §4 | PROFILE_* findings, `--json`; library of okf_lint.py |
| okf_index.py | Regenerates `index.md` per directory from frontmatter; skips what lint's scan leaves out (`.okfignore`, nested bundles, non-OKF directories), still listing a nested bundle in its parent's index; `--dir` into one exits 2 | `--check` for CI |
| okf_migrate.py | 0.1 ↔ 0.2, knowledge/2.0 → 3.0 (`--profile`), `--dry-run`, `--out`, `--keep-extensions`, `--file`; migrates only what okf_lint.py reads: the paths `.okfignore` matches and nested bundles (operational instances included) stay byte-identical; the profile step keeps those at the root where they are, together with a root directory that holds nothing else (a kind's directory of instances), moves those inside a moved directory with it and rewrites each `.okfignore` entry anchored under that directory to its new path | files + entry in log.md |
| okf_audit.py | Repository history for `okf-review`'s audit mode: concepts deleted or renamed since a reference point (read-only) | `--since`, `--json` |
| okf_projection.py | Knowledge projections ([ADR-0022](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md), [ADR-0031](/base/decisions/ADR-0031-projection-tools-transient-exception.md)): each `projection.yaml`, the dependency rule and drift by nature (`PROJ_*` codes, `PROJ_DRIFT` a warning); runs a rendered projection's `render` only with `--run-render`; `--record-hashes` writes a composed projection's hashes in place | `--json`, `--strict`, exit code |
| okf_obsidian.py | The Obsidian viewer setup of a bundle ([ADR-0032](/base/decisions/ADR-0032-obsidian-viewer-setup.md)), workspace configuration and not a knowledge projection: `.obsidian/app.json` (Markdown links relative, updated on rename), `.obsidian/.gitignore` and `knowledge.base` with five Bases views over `base/` and `fragments/`, which read the bundle's Domain Profile: each field with local names (field or value aliases) through a formula `okf_<field>`, Decisions also over the type aliases and local subtypes of Architecture Decision, By type through `okf_type`, which maps type aliases to their declared types (with no aliases, the fixed views byte for byte; with an unreadable profile or outside knowledge/3.0, the built-in names and one stderr line); never overwrites without `--force`; `just obsidian` runs it on this repository's `knowledge/` | `created` / `rewritten` / `skipped (exists)` per file, exit 2 without `index.md` or when a path it needs is taken |
| okf_common.py | Frontmatter parsing with PyYAML, Doc model, version detection | library |

Used by every skill that writes or checks a bundle, the fragment skills included: `okf-fragment` and `okf-distill` run `okf_index.py` and `okf_lint.py` (and `okf_migrate.py --file` in a 0.1 bundle), `okf-review` runs `okf_index.py`, `okf_lint.py` and `okf_audit.py`, `okf-init` offers `okf_obsidian.py`; see the [plugin](/base/systems/plugin-okf-builder.md).

# Examples

```bash
uv run <skills>/okf-standard/scripts/okf_lint.py knowledge --strict
uv run <skills>/okf-standard/scripts/okf_migrate.py knowledge --to 0.2 --dry-run
uv run <skills>/okf-standard/scripts/okf_projection.py knowledge --strict
uv run --with pytest <skills>/okf-standard/scripts/okf_lint.py --test
```

Without uv, `python3` works if PyYAML is installed; with neither, the scripts exit 2 with a message naming both fixes.

# Operation

* Tests: each script carries its own, run with `--test`; `just test` runs them and then the cross-script checks, each a named step of `build/checks.py` (init 0.1/0.2, Google fixtures v0.1 and v0.2, migration round-trip, the exported packages, the dogfood state).
* Decisions: [ADR-0011](/base/decisions/ADR-0011-uv-pep723-scripts.md) (supersedes ADR-0006), [ADR-0004](/base/decisions/ADR-0004-dual-support-v01-v02.md).
