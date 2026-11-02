---
name: okf-review
description: Runs the double check of an OKF bundle. Lists what changed since a reference point, the open and proposed conflicts of the Conflict Log, the open questions by owner and the draft concepts no person has verified, then records the person's decision on each conflict. Use when the user says "double check", "what is pending review", "review the knowledge changes", "resolve this conflict", "okf review", or after okf-distill has left a fragment in conflict.
---

# okf-review

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

The double check: shows a person what changed in the bundle, what is in dispute and what nobody has reviewed, and records what that person decides. It decides nothing itself.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop), **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`) and **its profile** (`okf_profile` in the root `index.md`; if missing, knowledge/2.0, the older profile). Write in that version and in that profile's layout.
   - **knowledge/2.0 bundle**: the typed directories sit at the root; drop the `base/` prefix from every directory, bundle path and `--dir` below (`/decisions/x.md`; indexes: `--dir <dir>`, `--dir fragments` when a fragment changed, then `--dir .`, with no `--dir base`), never mix the two layouts, and offer the migration to knowledge/3.0 with the `okf-migrate` skill, applied only after the person confirms.
2. **Pick the reference point**: the one the person gives (a commit, tag, branch or date); by default, the date of the last review recorded in `knowledge/log.md` (the latest `**Verification**` entry or `**Conflict**` entry that resolves or dismisses a conflict), or the most recent date section if there is none. Say which one is used, so the person can widen it.
3. **List the changes since then.** If the bundle is in Git (`git -C <bundle> rev-parse --is-inside-work-tree`), take them from Git: `git diff --name-status <ref> -- <bundle>` for a ref, or `git log --since=<date> --name-status --format='%h %ad %s' -- <bundle>` for a date, plus `git status --porcelain -- <bundle>` for what is not committed. Otherwise take them from the `log.md` entries of those dates. One line per concept: path, change, log label.
4. **List the conflicts** with state `open` or `proposed` in the Conflict Log (`/conflict-log.md` unless the bundle places it elsewhere; no Conflict Log means no conflicts): ID, source fragment, description, proposed resolution.
5. **List the concepts awaiting human verification**: take the drafts (`grep -rl "^status: draft" <bundle>/base <bundle>/*.md`; in 2.0, `grep -rl "^status: draft" <bundle>`), leave out the `Knowledge Fragment` and `Conflict Log` concepts (they stay drafts and are never verified) and keep those whose frontmatter has no `verified` entry with a `by` starting with `human:` (a `human:` in `generated` does not count). Show path, `type` and `generated`.
6. **List the open questions**: the `Open Question` concepts (`grep -rl "^type: Open Question" <bundle>/base`; in 2.0, `grep -rl "^type: Open Question" <bundle>`), grouped by `owner`. For each one with `question_status: open`: path, title, `blocks`, age and `review_on`. The age counts from the `occurred_at` of its `asked_in` fragment; without one, from its `generated.at`. Mark **due** when `review_on` is before today, as `okf-lint` does (`QUESTION_REVIEW_DUE`). Flag every `question_status: answered` without `answered_by`, and every question without `owner`. Answered and dropped questions are not listed otherwise.
7. **Present the four lists** and ask the person what to do with each conflict, one at a time:
   - **Resolved**, because the knowledge changed: a resolution that changes a decision is a new ADR that supersedes the old one, created with `okf-capture`; anything else is an **Update** of the concept, or a deprecation linking its replacement, applied with the `okf-capture` rules (concepts under `base/<dir>/`, bundle paths `/base/...`; never a concept in `projections/` or at the bundle root). Every concept the resolution creates, updates or deprecates, a new ADR included, cites the source fragment in `sources` (`resource: /fragments/<file>`) with `[^id]` footnotes on the claims it supports.
   - **Dismissed**, because it was a misunderstanding: the reason is required.
   - Not decided yet: the row stays `open`, or `proposed` with the resolution suggested.
   Suggest a resolution if useful, but never pick one: only the person decides.
   For an open question the person says no longer needs an answer: `question_status: dropped`, the reason under `# Answer`, a new `generated.at` and an **Update** log entry; its `status` does not change and it is never deleted. A question the person answers is answered with the `okf-capture` rules (the answering concept cites the question; the question gets `answered_by`).
8. **Record each decision** in the conflict's row: resolution, state (`resolved` / `dismissed` / `proposed`) and who decided, as the person's `human:<id>` (ask for it). Add `* **Conflict**: C-NNN resolved|dismissed by human:<id>: <resolution>` to `knowledge/log.md` under today's date, plus the **Creation** / **Update** / **Deprecation** entries of what the resolution changed.
9. **Release the fragment**: when none of a fragment's conflicts is `open` or `proposed` any more, set its `distillation_status: distilled` and update that item's outcome in its `# Distillation`. Nothing else in the fragment changes.
10. **Verification only on explicit confirmation.** Offer to mark the reviewed concepts; only for a concept the person explicitly confirms having reviewed, add `verified: { by: human:<id>, at: <now> }`, move it to `status: stable` and log `* **Verification**: ...`. Resolving a conflict or approving a change set is not a review: never add `verified` on that basis or on your own. Fragments and the Conflict Log are never verified or moved to `stable`.
11. **Index and validate** after any change:
    ```bash
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir base/<dir>     # each touched directory
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir fragments      # if a fragment changed
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir base
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
    uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
    ```
    Fix any ERROR before finishing.
12. **Close**: what was decided and by whom, what is still open (conflicts, and open questions by owner, the due ones first), and the concepts still awaiting review.
