---
type: Knowledge Fragment
title: 2026-11-04 · Building the knowledge audit and v0.9.0 with agent workflows
description: The working session that ran tickets A2 to A5 of the knowledge audit through agent workflows, released okf-builder 0.9.0, and drafted ADR-0028, with what each step taught about building with agents.
tags: [fragment, agents, workflow, audit, release]
status: draft
occurred_at: 2026-11-04
origin: Claude Code session in this repository (session_01EXD26xr5Q7ukXurEECSv4b), continued from 2026-11-03
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: pending
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "97c1b7d8e2376e5f5a9386a10e7523e6093ea427" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-04T22:28:27Z }
---

# Record

Written by the agent from its own session, in order. [The start of the session, A1's build on 2026-11-03, is known to the agent only from its context summary.] The repository commit above is main at the end of the session.

**A1 merged.** The owner said "mark #56 ready and merge it". PR #56 merged; the agent removed A1's worktrees and local branches with `git branch -d` after checking each was in main, and closed okf-flz.1. Deleting the remote branch was blocked for the agent as a destructive git action; the owner ran it.

**Ticket files lost.** The ticket files kept in the session's scratch folder were gone. The agent rebuilt `A2.md` and `common.md` from the beads, where the ticket text had been stored when the tickets were written.

**A2, first pre-flight.** The pre-flight stopped the build. `SECRET_IN_BUNDLE` was specified as "whatever `mask_secrets` would mask"; run over `knowledge/` that flagged 179 lines, 176 of them ADR file names in links. It also found that `FRAGMENT_CITED_PENDING` and `LINK_TO_RETIRED` would fire on the repo's own accepted ADRs, and that `FRAGMENT_LONG_PENDING` depended on today's date. In structured questions the owner moved `LINK_TO_RETIRED` and `SOURCE_UNCITED` to A5, dropped `FRAGMENT_CITED_PENDING`, made the pending age a metric only, and moved `VERIFICATION_NO_RECORD` to okf-yor. The owner asked whether gitleaks would be better; the agent answered that lint must stay free of external commands and run in Cowork and M365, and the owner chose a narrow detector in lint with gitleaks recommended for CI and a `make secrets` target.

**A2, second pre-flight.** The pre-flight found that the agent's previous claim was wrong: `mask_secrets` had no token-prefix patterns. Its key-value pattern also matched prose ("Keys: `types`") and the domain-profile template's comments. The owner chose a lint-side detector of its own. `SECTION_EMPTY` fired on every bundle `okf_init` creates; the owner chose to keep it and fix init. `VERIFIED_STALE` was limited to human verifications.

**A2, third pre-flight.** Data in the example bundle: ADR-0001 had been verified by a person and then rewritten by the knowledge/3.0 migration, and a distilled fragment's only output was a tracker item. The owner kept both as demo warnings. The fourth pre-flight passed.

**Builder killed by sleep.** About an hour into A2's build the machine slept and the builder died with "Your computer went to sleep mid-response". Its 25 changed files were uncommitted in its worktree. The agent saved them as a local WIP commit (9e710ae), freed the branch, added a `continueBranch` option to the workflow script, and resumed the run so the cached pre-flight was reused; the new builder finished and squashed the WIP. The owner asked whether `caffeinate` keeps the Mac awake; the agent explained `-i`, `-s`, `-m` and `-d`, that closing the lid on battery still sleeps, and corrected its own earlier suggestion (`caffeinate &` from `!` may not survive) to `nohup caffeinate -ims -t 10800 &`.

**A2 review: a secret printed.** Reviewers found that other checks (`BAD_STATUS`, `BROKEN_LINK`) printed the raw token that `SECRET_IN_BUNDLE` reported as "value not shown". The reviewer labelled it a fix; the agent treated it as blocking because the ticket's bar named "a secret value printed anywhere". A fix agent masked every finding, notice and `--json` field in one place. The agent verified it by planting a fake token in a status, a link query and a path segment: absent from the text, `--json` and `--profiles` output, and present three times in the source file as the control.

**A hollow comparison.** The agent's first comparison of lint output between main and the PR read the key `items`, which does not exist (the key is `findings`), so it compared two empty lists and reported "same". The agent noticed, said so, and redid it with the right key.

**Where things go.** The owner asked whether the workflows used for unattended jobs were documented in the knowledge base. They were in part (ADR-0009, the runbook Build a change in layers); the workflow script lived only in the session folder. The owner asked to design it: a doctrine that can be refined, and a review of what goes where (`tools/`, the knowledge bundle, the workspace). The agent drafted ADR-0028 (PR #58). The owner asked whether the standard and the templates should be maintained in the knowledge base; the agent recommended keeping them in the product, because a template's placeholders make it a broken concept and the standard's text has no OKF frontmatter, and the owner agreed. The owner chose generated root copies, `tools/` renamed `build/`, the agents policy kept apart from the doctrine, and a Doctrine local type.

**A3.** Three pre-flights. The first found that the standard's field types had no map, so `material` and `repository` could not be declared; the owner chose a `map` type. The second found that `FRAGMENT_MATERIAL_CHANGED`'s level conflicted with the rule that new codes are warnings; the owner chose an error. The agent's ticket had said the hash check "runs under `--no-profile` like the other okf-profile checks"; the builder found those checks are skipped under `--no-profile` and took the consistent reading, which the agent confirmed. Merging A3 made PR #58 conflict in the ADR index and `log.md`; the agent merged main into #58's branch keeping both entries.

**A4.** The agent told the owner that the distilled fragment in `knowledge/` linked every ledger row; it had read only the table's first rows. The pre-flight found the last row's Concept was `—`. The owner approved rewriting that one cell to `tracker`. Records here are bold-lead paragraphs, not headings, so the owner chose that lint checks the ledger's structure and A5 judges coverage. Pre-flight also found that okf-review's verification fragments never named their Concept cell; the agent added `okf-review/SKILL.md` to the ticket so they link the verified concept.

**A5.** The review found the git-facts script dropped non-ASCII paths, ignored lint's exclusions, counted any later log entry as recording a deletion, and reported an unstaged rename as a deletion. A fix agent corrected each. The agent verified in a throwaway repository: a deleted `decisión.md` reported, an unrelated Update not hiding a deletion, an unstaged rename reported as a rename, and the git index and object store byte-identical after the audit.

**Branch hygiene.** The owner asked whether merged branches needed deleting. Thirty merged branches remained on GitHub; the owner deleted them with one command the agent prepared, and turned on automatic deletion of head branches. The next merge (#61) deleted its branch by itself.

**v0.9.0.** The owner said "prepare the release", chose a PR (#62), then "merge #62" and "publish the v0.9.0 release". The agent rebuilt on the merge commit, tagged it with the full 40-hex commit, published the release with four files, and updated the local plugin. It notified the kdd-knowledge session with upgrade notes. That session ran 0.9.0 on its bundle and reported 26 `FRAGMENT_NO_LEDGER` warnings, a code the agent's notes had not named: the notes had been written without running the release on a bundle outside this repository. The agent sent a correction and, with the owner's approval, updated the published release notes.

**How the owner decided.** Each decision in this session was asked as a structured question with a recommendation, and the owner asked the agent to use structured questions to clear its doubts. Merging, publishing and deleting remote branches went through the owner's own words or commands.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
