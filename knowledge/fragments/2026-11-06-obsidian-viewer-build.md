---
type: Knowledge Fragment
title: 2026-11-06 · Building the Obsidian viewer setup (okf-ov8) with an agent workflow
description: The working session that settled ADR-0032 with the owner, ran ticket okf-ov8.1 through the okf-layer-ticket workflow and found, by opening the build in Obsidian, two defects that the tests and both fresh-context reviewers had passed.
tags: [fragment, agents, workflow, obsidian, verification]
status: draft
occurred_at: 2026-11-06
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "cd5cde205fd4ef342dca89852c57e4708880c32d" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-06T19:11:35Z }
---

# Record

Written by the agent from its own session, in order. The repository commit above is main after PR #75 merged.

**The bead predated the vocabulary.** The owner picked okf-ov8 from `bd ready`. Its text, written on 2026-10-31, called the setup an "Obsidian projection" extending ADR-0007. The agent read ADR-0022 decision 6, which since then gives "projection" to knowledge projections, and found that Obsidian reads `.obsidian/` only at the vault root, outside any `projections/<slug>/`. In structured questions the owner chose a script of its own, views scoped to `base/` plus a Fragments view, and committing the setup in this repository.

**An unasked addition, then a question.** The agent wrote ADR-0032 (PR #74) with a `.obsidian/.gitignore` that the owner had not been asked about, and said so in its summary. The owner asked what the file was, why it ignores what it ignores and its impact. The agent read the five files Obsidian had written in the prototype vault and explained them. The explanation raised a gap: ignoring `core-plugins.json` assumes Bases is on in a fresh vault, which the agent had not verified. The owner chose to keep the `.gitignore` and to check Bases on a fresh clone before accepting the build, and to move alias-aware views to a follow-up (okf-bic). The owner then said "merge #74".

**The workflow run.** On the owner's message "Launch OKF-OV 8.1" the agent ran `okf-layer-ticket` for okf-ov8.1. The pre-flight raised seven ambiguities and no owner decision. The builder proved each of seven criteria by revert, red and restore, and opened PR #75. The two reviewers found no blocking defect: one "to fix" (the tests did not pin each view's filters and columns to the ADR's table) and six nits.

**What the tests and reviewers passed.** The main session merged the branch into main in a scratch worktree (`make test` and `make lint` green) and, as the ticket's main-session verification required, opened that clean checkout's `knowledge/` as a new vault. Obsidian did not respond to the `obsidian://open` URL until the owner opened the folder by hand. Then:

- Bases was on by default, and the `.gitignore` kept Obsidian's new files out of git.
- `git status` showed the committed `app.json` modified: Obsidian had rewritten it without a final newline. Every clone opened in Obsidian would have shown a modified tracked file.
- `obsidian base:query` returned 67 rows in By type for 55 concepts on disk, and 5 in Fragments for 4 fragments. The JSON output showed that Bases' `file.name` has no extension, so the filter `file.name != "index.md"`, carried over from the 2026-10-31 prototype the owner had tested, never matched, and 13 `index.md` files were in the views.

Both defects passed the builder's tests and both reviewers: the tests checked the files the script wrote against the script's own constants, and no one had run the output in the tool that reads it. The agent tried `file.basename != "index"` in the live vault, and every view's count then matched the files on disk.

**The fix.** In a structured question the owner chose an inline fix by the main session, over a builder fix round, and to pin every view to the ADR's table in the same change. The agent fixed both constants, made the test assert each view's filters, grouping and columns and the exact bytes of `app.json`, showed each new assertion failing with its fix reverted (one revert first failed to apply because BSD sed does not take GNU's `0,/re/`, and was redone), and checked the committed files byte for byte against the ones Obsidian had read. The owner said "mark #75 ready and merge it". The first merge attempt failed because `--match-head-commit` needs a full SHA; the second merged.

**How the owner decided.** Each decision was asked as a structured question with a recommendation. When the agent put open decisions in prose at the end of a reply, the owner asked it to use structured questions instead; when the owner wanted to understand an option before choosing, they rejected the dialog and asked in words.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Provenance note (written by the agent from its own session) | — | context | no concept (provenance of the record) |
| The bead predated the vocabulary | Confirmation | applied | [ADR-0032](/base/decisions/architecture/ADR-0032-obsidian-viewer-setup.md) |
| An unasked addition, then a question | Confirmation | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| The workflow run | Confirmation | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| What the tests and reviewers passed | Addition | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| What the tests and reviewers passed | Update | applied | [Build a change in layers](/base/runbooks/build-in-layers.md) |
| The fix | Update | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
| How the owner decided | Confirmation | applied | [Building with agents](/base/doctrine/building-with-agents.md) |
