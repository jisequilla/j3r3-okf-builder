---
name: okf-review
description: Runs the double check of an OKF bundle. Lists what changed since a reference point, the open and proposed conflicts of the Conflict Log and the draft concepts no person has verified, then records the person's decision on each conflict. Use when the user says "double check", "what is pending review", "review the knowledge changes", "resolve this conflict", "okf review", or after okf-distill has left a fragment in conflict.
---

# okf-review

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

The double check: shows a person what changed in the bundle, what is in dispute and what nobody has reviewed, and records what that person decides. It decides nothing itself.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop) and **its version** (`okf_version` in the root `index.md`; if missing, `okf_lint.py --json` → `okf_version`). Write in that version.
2. **Pick the reference point**: the one the person gives (a commit, tag, branch or date); by default, the date of the last review recorded in `knowledge/log.md` (the latest `**Verification**` entry or `**Conflict**` entry that resolves or dismisses a conflict), or the most recent date section if there is none. Say which one is used, so the person can widen it.
3. **List the changes since then.** If the bundle is in Git (`git -C <bundle> rev-parse --is-inside-work-tree`), take them from Git: `git diff --name-status <ref> -- <bundle>` for a ref, or `git log --since=<date> --name-status --format='%h %ad %s' -- <bundle>` for a date, plus `git status --porcelain -- <bundle>` for what is not committed. Otherwise take them from the `log.md` entries of those dates. One line per concept: path, change, log label.
4. **List the conflicts** with state `open` or `proposed` in the Conflict Log (`/conflict-log.md` unless the bundle places it elsewhere; no Conflict Log means no conflicts): ID, source fragment, description, proposed resolution.
5. **List the concepts awaiting human verification**: take the drafts (`grep -rl "^status: draft" <bundle>`), leave out the `Knowledge Fragment` and `Conflict Log` concepts (they stay drafts and are never verified), and keep those whose frontmatter has no `verified` entry with a `by` starting with `human:` (a `human:` in `generated` does not count). Show path, `type` and `generated`.
6. **Present the three lists** and ask the person what to do with each conflict, one at a time:
   - **Resolved**, because the knowledge changed: a resolution that changes a decision is a new ADR that supersedes the old one, created with `okf-capture`; anything else is an **Update** of the concept, or a deprecation linking its replacement, applied with the `okf-capture` rules. Every concept the resolution creates, updates or deprecates, a new ADR included, cites the source fragment in `sources` (`resource: /fragments/<file>`) with `[^id]` footnotes on the claims it supports.
   - **Dismissed**, because it was a misunderstanding: the reason is required.
   - Not decided yet: the row stays `open`, or `proposed` with the resolution suggested.
   Suggest a resolution if useful, but never pick one: only the person decides.
7. **Record each decision** in the conflict's row: resolution, state (`resolved` / `dismissed` / `proposed`) and who decided, as the person's `human:<id>` (ask for it). Add `* **Conflict**: C-NNN resolved|dismissed by human:<id>: <resolution>` to `knowledge/log.md` under today's date, plus the **Creation** / **Update** / **Deprecation** entries of what the resolution changed.
8. **Release the fragment**: when none of a fragment's conflicts is `open` or `proposed` any more, set its `distillation_status: distilled` and update that item's outcome in its `# Distillation`. Nothing else in the fragment changes.
9. **Verification only on explicit confirmation.** Offer to mark the reviewed concepts; only for a concept the person explicitly confirms having reviewed, add `verified: { by: human:<id>, at: <now> }`, move it to `status: stable` and log `* **Verification**: ...`. Resolving a conflict or approving a change set is not a review: never add `verified` on that basis or on your own. Fragments and the Conflict Log are never verified or moved to `stable`.
10. **Index and validate** after any change:
    ```bash
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir <each touched directory>
    uv run "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
    uv run "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
    ```
    Fix any ERROR before finishing.
11. **Close**: what was decided and by whom, what is still open, and the concepts still awaiting review.
