---
type: System
title: OKF scripts
description: okf_init, okf_lint, okf_profile, okf_index, okf_migrate, okf_audit, okf_close, okf_projection and okf_obsidian (Python ≥ 3.9 and PyYAML, run with uv) in okf-standard/scripts.
resource: /plugin/okf-builder/skills/okf-standard/scripts
tags: [system, scripts, python]
status: stable
owner: human:jisequilla
runtime: uv
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T10:59:07Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:56:54Z }, { by: human:jisequilla, at: 2026-11-11T22:45:26Z }, { by: human:jisequilla, at: 2026-11-12T22:36:32Z }, { by: human:jisequilla, at: 2026-11-13T05:58:42Z }, { by: human:jisequilla, at: 2026-11-14T11:04:51Z }]
---

# Responsibility

| Script | Function | Output |
|---|---|---|
| okf_init.py | Scaffold of `knowledge/` (v0.2 or v0.1); `--instance <Kind> --id <id> --in <holder>` opens an operational instance in its kind's directory of the holder, its root `index.md` declaring `kind`, `state: open` and `parent: ../..`, and is refused in or below a domain bundle that declares `state: closed`; a `title` or `description` that would not read back as itself is written as a double-quoted YAML scalar; a new bundle gets `base/decisions/architecture/` | files; regenerates indexes |
| okf_lint.py | Spec conformance (§11) + profile; version detection; in a knowledge/3.0 bundle a decision's file is named in plain kebab-case or `<PREFIX>-NNNN-slug.md` with the prefix in force for its type, and another prefix is `NAME_KEBAB`; an open question of a closed instance is read through the Domain Profile's aliases | ERROR/WARN findings, `--json`, exit code |
| okf_profile.py | Loads and composes a knowledge/3.0 bundle's Domain Profile (built-in, `extends`, `base/profile.md`); `--check-builtin` checks the built-in profile against the standard's §4; for a type that is a `Decision` it gives the prefix in force (`prefix`, 2 to 5 capital letters no two types share) and, for any type, the directory in force (its own or that of the nearest type it extends that declares one) | PROFILE_* findings, `--json`; library of okf_lint.py |
| okf_index.py | Regenerates `index.md` per directory from frontmatter; skips what lint's scan leaves out (`.okfignore`, nested bundles, non-OKF directories), still listing a nested bundle in its parent's index; lists each kind's instances with their state in the kind directory's index, under the kind's description from the Domain Profile; `--dir` into one exits 2; writes no `index.md` in a hidden directory nor below a non-OKF directory (`--dir` into either exits 2); lists plain decisions under `# Decisions`, before `# Architecture decisions`, and describes a directory a type of the Domain Profile declares by that type's description | `--check` for CI |
| okf_migrate.py | 0.1 ↔ 0.2, knowledge/2.0 → 3.0 (`--profile`), `--dry-run`, `--out`, `--keep-extensions`, `--file`; migrates only what okf_lint.py reads: the paths `.okfignore` matches and nested bundles (operational instances included) stay byte-identical; the profile step keeps those at the root where they are, and keeps a root directory at the root only when it holds operational instances (nested bundles whose root `index.md` declares a `kind`) and no other document besides its `index.md` (a kind's directory of instances); it moves a root directory holding only ignored paths or nested bundles without `kind` under `base/` with them, moves those inside a moved directory with it and rewrites each `.okfignore` entry anchored under that directory to its new path, except one whose first segment is a glob, which it keeps and names in a `NOTICE` line; it regenerates the `index.md` of each root directory it keeps; `--move-decisions`, a step of its own on a knowledge/3.0 bundle, moves each decision that is not directly in the directory in force of its type to that directory under the same file name, rewrites the inline links, `sources` entries and path fields that point to it (inside a fragment's `# Record` only the link's target), regenerates the indexes of the directories it touched and those above, stops before writing when a new path is taken, ignored or in a nested bundle and on a closed bundle, and leaves `projections/` unedited with a `NOTICE` line | files + entry in log.md |
| okf_audit.py | Repository history for `okf-review`'s audit mode: concepts deleted or renamed since a reference point; it also looks inside each operational instance, with or without a reference point and outside git, and reports `EDITED_AFTER_CLOSE` for a concept of a closed instance whose `generated.at` is later than that instance's `closed_at` (read-only) | `--since`, `--json` |
| okf_close.py | Closes an operational instance into its parent ([ADR-0039](/base/decisions/ADR-0039-closing-operational-bundles.md)): report mode lists what blocks the closing (`NOT_INSTANCE`, `ALREADY_CLOSED`, `PARENT_CLOSED`, `CHILD_OPEN`, `PENDING_FRAGMENT`), the instance's concepts, its open questions and conflicts; `--apply` checks the closing fragment in the parent and each `--carry`, writes nothing when a check fails, then writes the carried questions and conflict rows, `state: closed` and `closed_at`, each file through a temporary file renamed over it, and regenerates both indexes; when a write or an index fails part way it names what is missing in one `ERROR:` line each and exits 3, a closing to finish by hand and never by running `--apply` again; not in the Microsoft 365 package | `--json`, `--apply`, `--dry-run`, exit code |
| okf_projection.py | Knowledge projections ([ADR-0022](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md), [ADR-0031](/base/decisions/ADR-0031-projection-tools-transient-exception.md)): each `projection.yaml`, the dependency rule and drift by nature (`PROJ_*` codes, `PROJ_DRIFT` a warning); runs a rendered projection's `render` only with `--run-render`; `--record-hashes` writes a composed projection's hashes in place | `--json`, `--strict`, exit code |
| okf_obsidian.py | The Obsidian viewer setup of a bundle ([ADR-0032](/base/decisions/ADR-0032-obsidian-viewer-setup.md)), workspace configuration and not a knowledge projection: `.obsidian/app.json` (Markdown links relative, updated on rename), `.obsidian/.gitignore` and `knowledge.base` with five Bases views over `base/` and `fragments/`, which read the bundle's Domain Profile: each field with local names (field or value aliases) through a formula `okf_<field>`, Decisions over `Decision`, every type that extends it and their aliases, By type through `okf_type`, which maps type aliases to their declared types (with no aliases, the fixed views byte for byte; with an unreadable profile or outside knowledge/3.0, the built-in names and one stderr line); never overwrites without `--force`; `just obsidian` runs it on this repository's `knowledge/` | `created` / `rewritten` / `skipped (exists)` per file, exit 2 without `index.md` or when a path it needs is taken |
| okf_common.py | Frontmatter parsing with PyYAML, Doc model, version detection; `inline_links`, a scanner of inline links as CommonMark defines them, used by `okf_migrate.py --move-decisions` while lint reads links with its own pattern | library |

Used by every skill that writes or checks a bundle, the fragment skills included: `okf-fragment` and `okf-distill` run `okf_index.py` and `okf_lint.py` (and `okf_migrate.py --file` in a 0.1 bundle), `okf-distill`'s Closing mode runs `okf_close.py`, `okf-review` runs `okf_index.py`, `okf_lint.py` and `okf_audit.py`, `okf-init` offers `okf_obsidian.py`; see the [plugin](/base/systems/plugin-okf-builder.md).

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
