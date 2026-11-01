---
name: okf-distill
description: Distills one pending knowledge fragment into the OKF bundle. Reads the concepts it touches, proposes a change set of additions, confirmations, updates, refutations and conflicts, and applies it only after the person approves, opening conflicts in the Conflict Log. Use when the user says "distill this fragment", "what does this meeting change", "process the pending fragments", "okf distill", or after okf-fragment has captured an event.
---

# okf-distill

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Turns what a fragment records into changes to the bundle's concepts. It proposes; the person decides. Nothing is written before the person approves the change set, and approving a change set is not reviewing a concept: distillation never sets `verified`.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop) and **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`). Write in that version.
2. **Pick one fragment.** The one the person names, or list the pending ones (`grep -l "distillation_status: pending" <bundle>/fragments/*.md`) and ask. One fragment per run. If it is `distilled`, say so and stop unless the person asks to distill it again; if it is `conflict`, point to `okf-review`.
3. **Read the context**: the root `index.md`, the `index.md` of each directory the fragment touches, the concepts it names or contradicts (systems, ADRs, terms, runbooks) and the Conflict Log (`/conflict-log.md` unless the bundle places it elsewhere), so an open conflict is not opened twice. Read the fragment's `# Record`; never edit it.
4. **Classify each item** of knowledge in the record into one of five kinds, each with its target concept (an existing path, or the type and path of a new one):

   | Kind | When | Proposed change |
   |---|---|---|
   | Addition | The fragment brings knowledge the bundle lacks | A new concept, or a new part of one |
   | Confirmation | The fragment states what a concept already says | The fragment is added to the concept's `sources` |
   | Update | The fragment refines a concept and contradicts nothing | The concept is edited, with an **Update** log entry |
   | Refutation | The fragment makes a concept outdated and names or implies its replacement, and nobody in the record disputes it | The concept is deprecated and links to its replacement (for an ADR, a new ADR that supersedes it); a **Deprecation** log entry; no conflict is opened |
   | Conflict | The fragment contradicts a concept and it is unclear which is right: participants disagree, sources disagree, or the replacement is not known | A row in the Conflict Log |

   **When in doubt between refutation and conflict, it is a conflict.** Small talk and questions left unanswered are not items; an open question worth keeping is listed with outcome `not distilled`.
5. **Propose the change set** and stop: one table grouped by kind, with Item · Kind · Target concept · Proposed change · Evidence (speaker and timestamp in the record). Ask the person to approve, change or reject each item. **Apply nothing until the person approves.** Rejected items are not applied and are recorded as `rejected`.
6. **Apply the approved items** with the `okf-capture` rules (template `<skills>/okf-standard/templates/<type>.md`, `status: draft` on creation, actor `okf-builder/<model>`, one-sentence `description`, bundle-absolute links, no placeholders). Every concept created, confirmed, updated or deprecated cites the fragment in `sources` (`{ id: <id>, resource: /fragments/<file>, title: ... }`) with `[^id]` footnotes on the claims it supports.
   - **Addition**: create the concept, or add the part to an existing one and update its `generated`.
   - **Confirmation**: add the fragment to the concept's `sources` and attach its footnote to the sentence that already states the confirmed claim. Write no new sentence: if no sentence states it, the item is an Update. Update `generated` (`by`, `at`) and leave `verified` as it is, so the gap since the last verification stays visible.
   - **Update**: edit the concept and update `generated` (`by`, `at`); leave `verified` as it is (the gap between `verified` and `generated.at` is information).
   - **Refutation**: set `status: deprecated` on the outdated concept and link its replacement in the body; never delete it. For an ADR, create the new ADR with `supersedes`, and give the old one `decision_status: superseded` and `superseded_by`. No Conflict Log row.
   - **Conflict**: the concept in dispute is not changed. Add a row to the Conflict Log; if the bundle has none, create `conflict-log.md` at the bundle root from `<skills>/okf-standard/templates/conflict-log.md` (with a **Creation** log entry). Row: `C-NNN` (highest existing + 1, three digits) · source (a link to the fragment, `/fragments/<file>`) · description (who or what says each side) · kind (participants disagree, sources disagree, contradiction with an accepted ADR, replacement unknown) · resolution (empty, or the one proposed) · state `open`, or `proposed` when a resolution awaits a person · decided `—`.
   - **0.1 bundle**: after saving each new or changed concept, run `uv run "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <relative-path>`; 0.1 has no `status`, so a deprecated concept says so in the first line of its body, with the link to its replacement.
7. **Fill the fragment's `# Distillation`**: one row per item, with Item · Kind · Outcome (`applied`, `rejected`, `not distilled`, `open: C-NNN` or `proposed: C-NNN`, matching the row's state) · Concept (links). Set `distillation_status: distilled`, or `conflict` while any of its conflicts is `open` or `proposed`. Nothing else in the fragment changes.
8. **Never add `verified`** and never move a concept to `stable`, even if the person approved the change set: that is a separate, explicit review (`okf-review`).
9. **Log** under today's date in `knowledge/log.md` (and the directory's own `log.md` if it has one), each linking its concept and the fragment: `* **Creation**: ...`, `* **Update**: ...` (also for confirmations), `* **Deprecation**: ... superseded by ...`, `* **Conflict**: C-NNN opened in the conflict log from <fragment>`, linking both. Use only these labels. The person's approval goes inside the entries (`approved by human:<id>`), never under a label of its own.
10. **Index and validate**:
    ```bash
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir <each touched directory>
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
    uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
    ```
    Fix any ERROR before finishing.
11. **Close**: list what was applied, rejected and left open (with the `C-NNN` IDs), describing each change as it is in the files (from `git diff` when the bundle is in Git), never as smaller than it is; remind the person that the new and changed concepts stay `draft` and unverified, and point to `okf-review` to resolve the conflicts and review the concepts.
