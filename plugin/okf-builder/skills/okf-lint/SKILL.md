---
name: okf-lint
description: Validates that knowledge/ complies with the OKF v0.2 spec and the knowledge/2.0 profile (frontmatter, type, index/log, actors, ISO 8601, links, staleness, out-of-date indexes). Use when the user says "validate the knowledge", "okf lint", "check the bundle", "is knowledge/ well formed?", or before a commit/PR that touches knowledge/.
---

# okf-lint

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`.

## Steps

1. Run:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_lint.py" [<bundle>] [--json] [--strict] [--no-profile] [--okf-version auto|0.1|0.2]
   ```
   Without an argument it searches for `knowledge/` upwards from the cwd. `--no-profile` validates only the spec (useful for external bundles). `--okf-version auto` (the default) uses `okf_version` from the root `index.md` or infers it; the last line of output reads `OKF <version> (<origin>)`.
2. Interpret the output:
   - `ERROR` breaks conformance (no frontmatter, no `type`, invalid YAML, invalid `status`, malformed `index`/`log`, missing `index.md`/`log.md`/`project.md`, missing `generated`, Attested Computation without `runtime`/computation).
   - `WARN` is guidance: broken links (`BROKEN_LINK`), `STALE`, `INDEX_STALE`, no `description`, malformed actors or dates, names that aren't kebab-case.
   - Versions: `LEGACY_TIMESTAMP`/`LEGACY_CITATIONS` (0.1 forms in a 0.2 bundle), `V02_FIELD_IN_V01` (0.2 keys in a 0.1 bundle, kept as they are), `MIXED_VERSIONS` (half migrated), `NO_OKF_VERSION` (root doesn't declare a version), `VERSION_MISMATCH`. All of them are resolved with `okf-migrate` or by declaring `okf_version`.
3. Propose concrete fixes per file. For `INDEX_STALE` run `okf-index`. For `STALE` list the concepts and ask the user to decide: renew `stale_after`, update the content or deprecate. For `BROKEN_LINK` offer `okf-capture` for the missing concept.
4. If the user asks for it, apply the mechanical fixes (date format, `status`, regenerating indexes) and run again until there are 0 errors. Don't touch semantic content or `verified` without confirmation.
5. To add it to CI, propose:
   ```yaml
   # .github/workflows/okf-lint.yml
   - run: python3 tools/okf/okf_lint.py knowledge --strict
   ```
   copying `scripts/okf_common.py` and `okf_lint.py` into the repo's `tools/okf/` (no dependencies).
