---
type: Runbook
title: Run a verification round
description: Steps to have a person verify concepts on the Knowledge Viewer in this repository, from building the page with okf_viewer.py to writing verified from the APPLY rows of okf_viewer.py --answers, as okf-review step 11 runs them.
tags: [runbook, verification, review, viewer]
status: draft
owner: human:jisequilla
stale_after: 2027-05-15T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T21:48:55Z }
sources:
  - { id: skill, resource: plugin/okf-builder/skills/okf-review/SKILL.md, title: "okf-review, step 11" }
  - { id: sdr-0022, resource: /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md }
---

# Trigger

Concepts in status draft wait for a person's verification (`okf-review` lists them), or lint reports `VERIFIED_STALE` on a concept edited after its verification, and the person chooses to answer on the [Knowledge Viewer](/base/systems/knowledge-viewer.md) rather than by structured question. The steps are those of `okf-review` step 11, the review page channel, with this repository's paths; where they differ, the skill is right.

# Steps

1. **Build** the page from a committed tree: `just viewer`, which runs `uv run plugin/okf-builder/skills/okf-standard/scripts/okf_viewer.py knowledge --out dist/viewer --force`. For a round of chosen concepts, add `--round <name> --paths <bundle path> ...`; without them the round is every `base/` draft no person verified at its current `generated.at`. When it reports `(dirty)`, commit the bundle's changes first and build again, so the page names a commit that exists.
2. **Publish** `dist/viewer/index.html` and `dist/viewer/concepts.json` to the page, `https://claude.ai/artifact/Tuhiidxvb6RtxXEuUUzszE`, with the platform's artifact tool: same URL, capabilities unchanged, so the stored answers stay. The page is shared with nobody.
3. **The person answers** on the page: Confirm this version or Not confirmed, with an optional comment on the second.
4. **Check the answers**, only when the person asks in the session: export the collection `answers` with the platform's database tool (a directory of `<id>.json` files, or a JSON list carrying each answer's `id` and `version` from the listing), then run `uv run plugin/okf-builder/skills/okf-standard/scripts/okf_viewer.py knowledge --answers <export> --json`, with `--since <answered_at of the last answer applied>` to read only the newer ones. It writes nothing.
5. **Keep the answers** verbatim as a fragment with `okf-fragment`, each with its store id and version: `origin` the session or the page, `participants` the person and the agent, `occurred_at` the time of the answers, `distillation_status: distilled`, and in `# Distillation` one row per concept (Kind `—`, Outcome `verified` or `not confirmed`).
6. **Apply only the `APPLY` rows**: for each, add `verified: { by: human:<id>, at: <answered_at> }` and `status: stable`, then one `* **Verification**: ...` entry in `log.md` naming the concepts and linking the fragment.
7. **Index and validate**: `uv run plugin/okf-builder/skills/okf-standard/scripts/okf_index.py knowledge`, then `just lint`, at 0 errors and with no `VERIFIED_STALE` on the concepts verified.

# Rollback

- A `STALE` row: apply nothing; the concept changed since the page was built, so build and publish again and ask the person to answer that version.
- A `NOT_CONFIRMED` row: the concept stays draft. Its comment is the person's reason: propose the change it asks for with `okf-capture`, never apply it unasked.
- `UNKNOWN` and `NOT_VERIFIABLE` rows: apply nothing and tell the person.
- A page built from a dirty tree names a commit that does not hold what it showed: apply nothing from it, commit, build and publish again, and ask again.
- A `verified` written in error is removed by hand, with the concept back in status draft and a log entry saying why.
