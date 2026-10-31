---
name: okf-standard
description: 'Knowledge of the OKF standard (Google''s Open Knowledge Format v0.1 and v0.2), the differences between them, and the knowledge/2.0 profile for repos. Load it when the user asks what OKF is, how to structure knowledge/, which fields the frontmatter carries, which type to use, how to write an ADR/runbook/metric in OKF, or when another okf-* skill needs the spec. Triggers: "OKF", "open knowledge format", "knowledge structure", "knowledge/", "OKF frontmatter", "OKF bundle", "OKF ADR template", "OKF 0.1 vs 0.2", "OKF version".'
---

# OKF standard · knowledge/2.0 profile

This skill is the source of truth for the standard inside the plugin. The other skills (`okf-init`, `okf-capture`, `okf-lint`, `okf-index`, `okf-ask`) assume it.

## Operating summary (what to always keep in mind)

- A bundle = the `knowledge/` directory at the repo root. Only markdown + YAML frontmatter.
- Reserved files: `index.md` (listing per directory, no frontmatter except the root one with `okf_version`) and `log.md` (history, `## YYYY-MM-DD` dates, most recent first).
- Every non-reserved `.md` is a **concept**. The only required field: `type`.
- The knowledge/2.0 profile also requires `generated: { by: <actor>, at: <ISO 8601> }` and the presence of `index.md`, `log.md` and `project.md` (`type: Project`).
- Actors: `human:<id>` · `process:<id>` · `<agent>/<version>`. When this plugin writes content, it uses `okf-builder/<model>` as the actor in `generated.by`; **never** invent a `verified` with `human:`: only the person adds it.
- Links between concepts: bundle-absolute `[x](/systems/x.md)`. Broken links = pending knowledge, not an error.
- Lifecycle: `status: draft|stable|deprecated` (absent ⇒ stable), `stale_after` an absolute instant. Never delete: deprecate and link to the replacement.
- Provenance: `sources[]` with a required `resource`, and an `id` if the body cites it with `[^id]`.

## Profile directory structure

```
knowledge/
  index.md  log.md  project.md
  architecture/  decisions/  domain/  systems/  apis/  data/
  metrics/  computations/  runbooks/  playbooks/  policies/  references/
```

All subdirectories are optional; each one has its own `index.md`.

## `type` vocabulary → directory → template

| type | directory | template |
|---|---|---|
| Project | root | `<skills>/okf-standard/templates/project.md` |
| Architecture View | architecture/ | `<skills>/okf-standard/templates/architecture-view.md` |
| Architecture Decision | decisions/ (`ADR-NNNN-slug.md`) | `<skills>/okf-standard/templates/adr.md` |
| Term / Glossary | domain/ | `<skills>/okf-standard/templates/term.md` |
| System | systems/ | `<skills>/okf-standard/templates/system.md` |
| API | apis/ | `<skills>/okf-standard/templates/api.md` |
| Table / Dataset | data/ | `<skills>/okf-standard/templates/table.md` |
| Metric | metrics/ | `<skills>/okf-standard/templates/metric.md` |
| Attested Computation | computations/ | `<skills>/okf-standard/templates/computation.md` |
| Runbook | runbooks/ | `<skills>/okf-standard/templates/runbook.md` |
| Playbook | playbooks/ | `<skills>/okf-standard/templates/playbook.md` |
| Policy | policies/ | `<skills>/okf-standard/templates/policy.md` |
| Reference | references/ | `<skills>/okf-standard/templates/reference.md` |

The templates use `{{name}}` placeholders; replace all of them before saving. If a placeholder doesn't apply, remove the line rather than leaving it empty.

## Versions: v0.2 (default) and v0.1

- A bundle is **0.1** if its root `index.md` declares `okf_version: "0.1"`, or if its concepts use `timestamp` / `# Citations` without any 0.2 key. It is **0.2** in every other case.
- Two breaking changes: `timestamp` → `generated: { by, at }` and `# Citations` (body, `[n] [title](url)` or `- url`) → `sources[]` (frontmatter) + `[^id]` footnotes. Everything else in 0.2 (`verified`, `status`, `stale_after`, actors, Attested Computation, required offset in dates) is additive.
- **Always write in the bundle's version.** In a 0.1 bundle: `timestamp` instead of `generated`, citations under `# Citations`, no `status`/`verified`/`stale_after`. The templates are 0.2; for a 0.1 bundle fill in the template and run `okf_migrate.py --to 0.1 --file <path>`.
- A 0.2 consumer reads 0.1 (falling back to `timestamp` and `# Citations`); a 0.1 consumer reads 0.2 by ignoring unknown keys. Never mix forms in one bundle.
- Full matrix, mapping rules and exchange policy: `references/OKF-COMPATIBILITY.md`. Migration: the `okf-migrate` skill.

## Where everything is (`<skills>` convention)

`<skills>` = the directory that holds the `okf-*` skills (the parent of this skill). This skill carries the scripts and templates the others use:

```
<skills>/okf-standard/scripts/okf_init.py | okf_lint.py | okf_index.py | okf_migrate.py | okf_common.py
<skills>/okf-standard/templates/*.md
<skills>/okf-standard/references/OKF-STANDARD.md | OKF-COMPATIBILITY.md | OKF-SPEC-v0.1.md | OKF-SPEC-v0.2.md
```

Python ≥ 3.9 and PyYAML; run with `uv run`, which installs PyYAML, or with `python3` where PyYAML is installed. If the environment cannot run scripts (for example some M365 agents), apply the rules by hand from `references/` and say so.

## When to read the references

- Detailed profile questions (naming rules, lifecycle, conformance): read `references/OKF-STANDARD.md`.
- Spec questions (sources, verified, Attested Computation, conformance §11): read `references/OKF-SPEC-v0.2.md`; for older bundles, `references/OKF-SPEC-v0.1.md`. These are verbatim copies of Google's spec, licensed under `references/OKF-SPEC-LICENSE.md`.
- Differences between versions and field mapping: `references/OKF-COMPATIBILITY.md`.

## Concept writing rules

1. `description`: one sentence, no redundant final period, useful out of context (it appears in indexes and search tools).
2. Structured body: tables and lists before prose. The headings `# Schema`, `# Examples`, `# Computation` have a conventional meaning.
3. One concept = one unit of knowledge. If a document covers three metrics, they are three concepts linked from one narrative concept.
4. Cite external sources with `sources[]` + a footnote; don't copy external text verbatim.
5. On create or change: an entry in `log.md` (root and, if there is one, the directory's) and regenerate `index.md` (`okf-index`).
