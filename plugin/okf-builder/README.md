# okf-builder

A Claude Code / Cowork plugin that manages a project's knowledge as an **OKF bundle** (Open Knowledge Format v0.2, Google) inside `knowledge/` in each repository.

## Skills

| Skill | What it does |
|---|---|
| `okf-standard` | Knowledge of the standard and the `knowledge/2.0` profile; concept templates. |
| `okf-init` | Creates the `knowledge/` structure in the current repo. |
| `okf-capture` | Adds a concept (ADR, runbook, system, API, table, metric, term, policy…) with its template, log and index. |
| `okf-fragment` | Captures a meeting, transcript, chat or slide deck as a knowledge fragment, recorded as it happened. |
| `okf-distill` | Proposes what one fragment changes in the bundle (additions, confirmations, updates, refutations, conflicts) and applies only what the person approves. |
| `okf-review` | The double check: changes since the last review, open conflicts and unverified drafts; records the person's decision on each conflict. |
| `okf-lint` | Validates conformance with the spec and the profile. |
| `okf-index` | Regenerates the `index.md` files from the frontmatter. |
| `okf-ask` | Answers questions about the project by navigating the bundle and citing sources and trust level. |
| `okf-migrate` | Detects the OKF version and migrates 0.1 ↔ 0.2 (with `--out` to export downgraded copies). |

## Scripts (Python ≥ 3.9 and PyYAML; run with `uv run`)

In `skills/okf-standard/scripts/` (the skills reference them as `<skills>/okf-standard/scripts/`):

```
okf_init.py   --root . --title "…" --description "…" --actor human:<id>
okf_lint.py   [knowledge] [--json] [--strict] [--no-profile]
okf_index.py  [knowledge] [--check] [--dir sub]
okf_migrate.py [knowledge] --to 0.2|0.1 [--actor A] [--keep-extensions] [--out DIR] [--dry-run] [--file rel.md]
```

They can be copied into `tools/okf/` of any repo for CI; the CI job needs uv (for example `astral-sh/setup-uv`) or PyYAML.

## Standard

`skills/okf-standard/references/OKF-STANDARD.md` defines the profile; `OKF-COMPATIBILITY.md` holds the v0.1↔v0.2 matrix. Original specs in `references/OKF-SPEC-v0.1.md` and `OKF-SPEC-v0.2.md` (Apache-2.0, GoogleCloudPlatform/knowledge-catalog).
