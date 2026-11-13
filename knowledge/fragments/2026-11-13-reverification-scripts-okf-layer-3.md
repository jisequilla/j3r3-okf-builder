---
type: Knowledge Fragment
title: 2026-11-13 · Re-verification of the OKF scripts after okf-3vg.6 and okf-3vg.12
description: The owner's answer to a structured question confirming OKF scripts at generated.at 2026-11-13T05:53:42Z, after okf-3vg.6 changed its okf_audit.py row and okf-3vg.12 added okf_close.py and okf_init's --instance.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-13T05:58:42Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "d7c6dc6133a00fea8a4ca476fe510f7f2737c10a" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-13T05:58:42Z }
---

# Record

okf-3vg.6 (PR #107) edited the `okf_audit.py` row of [OKF scripts](/base/systems/scripts-okf.md), which human:jisequilla had verified on 2026-11-12, and okf-3vg.12 then added the `okf_close.py` row, `--instance` on the `okf_init.py` row, `okf_close` in the description and okf-distill's Closing mode in the usage line, on branch `okf-3vg-12` from `d7c6dc6`. The owner chose to verify once for both. The agent showed the five changes and asked in the session's question tool. Kept verbatim.

**Question** (header "scripts-okf")

> Do you verify 'OKF scripts' (knowledge/base/systems/scripts-okf.md) at generated.at 2026-11-13T05:53:42Z, branch okf-3vg-12 on main d7c6dc6? Since your verification of 2026-11-12 these changed. (1) The description now lists okf_close. (2) The okf_init.py row adds: '--instance <Kind> --id <id> --in <holder> opens an operational instance in its kind's directory of the holder, its root index.md declaring kind, state: open and parent: ../..'. (3) A new okf_close.py row: 'Closes an operational instance into its parent (ADR-0039): report mode lists what blocks the closing (NOT_INSTANCE, ALREADY_CLOSED, PARENT_CLOSED, CHILD_OPEN, PENDING_FRAGMENT), the instance's concepts, its open questions and conflicts; --apply checks the closing fragment in the parent and each --carry, writes nothing on any failure, then writes the carried questions and conflict rows, state: closed and closed_at, and regenerates both indexes; not in the Microsoft 365 package', with output '--json, --apply, --dry-run, exit code'. (4) The okf_audit.py row adds (#107): 'it also looks inside each operational instance, with or without a reference point and outside git, and reports EDITED_AFTER_CLOSE for a concept of a closed instance whose generated.at is later than that instance's closed_at'. (5) The usage line adds 'okf-distill's Closing mode runs okf_close.py'.
>
> Options: "Verify" (I record your answer verbatim as a fragment (ADR-0033) in the same PR, and the concept goes back to stable. Once the PR merges, main is green at --strict. Right if all five changes read correctly to you.) · "Read it first" (You open the file on branch okf-3vg-12 and answer later. I push the PR as a draft, and main stays red at --strict until you answer. Right if you want to read the rows inside their full table.) · "Change something" (Write in the note what doesn't fit. I fix it on the branch and ask again, and main stays red meanwhile. Right if any row describes a script wrongly.)

**Answer**: "Verify"

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Question | — | verified | [OKF scripts](/base/systems/scripts-okf.md) |
