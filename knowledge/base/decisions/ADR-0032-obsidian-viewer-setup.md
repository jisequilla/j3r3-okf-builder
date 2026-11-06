---
type: Architecture Decision
title: "ADR-0032: A bundle opens as an Obsidian vault through a viewer setup that a script writes, not a projection"
description: okf_obsidian.py writes .obsidian/app.json, with Markdown links kept relative and updated on rename, and knowledge.base, with five Bases views over base/ and fragments/, at a bundle's root without overwriting; it is workspace configuration for one tool, neither a knowledge projection nor a platform package; okf-init offers it, make obsidian runs it here, and this repository commits both files.
tags: [adr, obsidian, viewer, workspace]
status: draft
adr_id: ADR-0032
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-06T17:45:19Z }
sources:
  - { id: okf-1b5, resource: "bead okf-1b5", title: "OKF inside Obsidian: bundle as a vault (closed 2026-10-31)" }
  - { id: okf-ov8, resource: "bead okf-ov8", title: "Obsidian projection: vault config and Bases views for a bundle" }
  - { id: adr-0022, resource: /base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md }
  - { id: standard, resource: plugin/okf-builder/skills/okf-standard/references/OKF-STANDARD.md, title: "OKF standard, §3.3 Links" }
---

# Context

On 2026-10-31 this repository's `knowledge/` was opened as an Obsidian vault to see whether Obsidian could serve as a reader for a bundle. Bundle-absolute links resolve from the vault root, the graph view was judged good by the owner, and a Bases file showed the concepts as tables that read nested `generated.by` and `generated.at`. A renamed file broke the links to it unless Obsidian writes Markdown links in relative form and updates them on rename[^okf-1b5]. The prototype `.obsidian/app.json` and `knowledge.base` have stayed in the repository since then, excluded from git.

The follow-up bead called the setup an "Obsidian projection" extending ADR-0007[^okf-ov8]. That bead predates profile knowledge/3.0 and ADR-0022. Since ADR-0022, "projection" means a knowledge projection, a directory `projections/<slug>/` derived from base concepts, and the per-platform outputs of the skills are platform packages[^adr-0022]. The Obsidian setup is neither. Obsidian reads `.obsidian/` only at the vault root, so it cannot live in `projections/<slug>/`. It packages no skills. It configures one tool for reading a bundle, which is the workspace home of ADR-0028[^adr-0028].

The prototype base also predates the layers: it lists every Markdown file but `index.md` and `log.md`, so fragments, `project.md` and the Conflict Log appear among the concepts.

The repository's owner, human:jisequilla, decided what the setup is, how its views are scoped and what this repository commits, in answer to structured questions on 2026-11-06.

# Decision

1. **A viewer setup, not a projection.** A bundle opens in Obsidian with its root as the vault, so bundle-absolute links resolve. The two files that make it readable there are workspace configuration for one tool (ADR-0028 decision 1), neither a knowledge projection (ADR-0022 decision 6) nor a platform package ([ADR-0007](/base/decisions/ADR-0007-single-source-and-projections.md)). No OKF tool reads them: `okf_lint` skips dot directories and reads only Markdown files, so neither file needs a lint change.
2. **A script writes them.** `okf_obsidian.py`, in `okf-standard/scripts/` with the other scripts, takes a bundle root and writes:
   - `.obsidian/app.json` with `useMarkdownLinks: true`, `newLinkFormat: "relative"` and `alwaysUpdateLinks: true`;
   - `.obsidian/.gitignore`, which ignores everything in `.obsidian/` but `app.json` and itself, so a bundle in git keeps the setting and not each reader's window state, plugins or graph;
   - `knowledge.base` at the bundle root, with the views of decision 3.

   As `okf_init.py` does, it never overwrites an existing file unless given `--force`, reports what it wrote and what it left, and is idempotent. It carries a `--test` that `make test` runs. The `okf-init` skill offers it after creating a bundle and on request for an existing one; `make obsidian` runs it on this repository's `knowledge/`. It ships wherever `okf_init.py` ships.
3. **Five views, by layer.** The base's global filter keeps Markdown files other than `index.md` and `log.md`; each view adds its layer:

   | View | Layer | Filter | Grouping and columns |
   |---|---|---|---|
   | Decisions | `base/` | `type == "Architecture Decision"` | grouped by `decision_status`; name, title, decision status, status, written at |
   | Awaiting human review | `base/` | `status == "draft"` | name, type, written by, written at |
   | By type | `base/` | none | grouped by `type`; name, description, status |
   | Going stale | `base/` | `stale_after` set | name, type, `stale_after`, days to stale |
   | Fragments | `fragments/` | none | grouped by `distillation_status`; name, `occurred_at`, `origin`, `participants` |

   "Written by", "written at" and "days to stale" are the prototype's formulas over `generated.by`, `generated.at` and `stale_after`.
4. **Links may become relative on rename.** With decision 2's settings, Obsidian rewrites the links to a renamed file in relative form. The standard recommends bundle-absolute links and allows relative ones (§3.3)[^standard], so a rename in Obsidian leaves valid links in the allowed form, not the recommended one. That is accepted: the alternative is links that break.
5. **This repository commits the setup.** `knowledge/knowledge.base`, `knowledge/.obsidian/app.json` and `knowledge/.obsidian/.gitignore` are committed, so anyone who clones the repository and opens `knowledge/` in Obsidian gets the views. The lines of `.git/info/exclude` that hid the prototype are removed.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| A rendered knowledge projection `projections/obsidian/` | Uses the projection tools; drift checked by `--run-render` | `.obsidian/` must sit at the vault root, outside the projection's directory; the setup derives from no base concept | It bends ADR-0022's definition |
| A flag of `okf_init.py` (`--obsidian`) | Nothing new to package | An existing bundle gets it only through init's required `--title` and `--description` | A separate script serves new and existing bundles alike |
| A platform package (`make obsidian` writing to `dist/`) | Nothing in the bundle | A reader must copy two files into the bundle by hand; the setup packages no skills | It is not what a platform package is |
| Keep the prototype's views over every Markdown file | Already tested | Fragments, `project.md` and the Conflict Log mix with the concepts in every view | The layers are what a reader navigates by |
| Views over `base/` only | Four tested views, one filter added | Pending fragments, the layer a person distills from, stay invisible | A fifth view costs one block |
| Keep the setup local in this repository | Nothing per-tool committed | A clone gets no views; the generator is never dogfooded where it is built | The owner chose to commit it |
| Absolute link format in Obsidian | Keeps the recommended form | Renames broke links in the 2026-10-31 test | Valid links matter more than the recommended form |

# Consequences

- Positive: any bundle becomes browsable in Obsidian with one command, its decisions, drafts, stale concepts and pending fragments as tables, and links that survive renames; this repository's clone opens that way as it is.
- Negative / accepted debt: one more script in every package that carries `okf_init.py`; renames made in Obsidian turn bundle-absolute links relative; the views name fields of the built-in Domain Profile (`decision_status`, `distillation_status`, `stale_after`), so a bundle whose Domain Profile renames them through aliases sees empty columns; Obsidian is not open source, so readers without it still need the web viewer of okf-1lj.
- Follow-up actions: build the script, its test, the `okf-init` step, `make obsidian` and the packaging; commit this repository's setup; the [OKF scripts](/base/systems/scripts-okf.md) and the [okf-builder plugin](/base/systems/plugin-okf-builder.md) list the script.

# Related

* [ADR-0022: Knowledge projections](/base/decisions/ADR-0022-knowledge-projections-drift-by-nature.md)
* [ADR-0028: Where things go](/base/decisions/ADR-0028-where-things-go.md)
* [ADR-0014: A knowledge repository has one source; other tools read it](/base/decisions/ADR-0014-knowledge-repository-storage.md)

[^okf-1b5]: Bead okf-1b5, close reason.
[^okf-ov8]: Bead okf-ov8, description.
[^adr-0022]: ADR-0022, decisions 1, 5 and 6.
[^adr-0028]: ADR-0028, decision 1.
[^standard]: OKF standard, §3.3.
