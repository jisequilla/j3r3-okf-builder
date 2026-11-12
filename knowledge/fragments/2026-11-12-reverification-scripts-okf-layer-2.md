---
type: Knowledge Fragment
title: 2026-11-12 · Re-verification of the OKF scripts after okf-3vg.9 and okf-3vg.3
description: The owner's answer to a structured question confirming OKF scripts at commit e759f5d, generated.at 2026-11-12T04:06:05Z, after okf-3vg.9 and okf-3vg.3 changed its okf_migrate.py and okf_index.py rows.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-12T22:36:32Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "e759f5d85007ca0401863732c1e02acad0697c7b" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-12T22:36:32Z }
---

# Record

okf-3vg.9 (PR #100) and okf-3vg.3 (PR #101) each edited one row of [OKF scripts](/base/systems/scripts-okf.md), which human:jisequilla had verified on 2026-11-11; as the runbook plans for a layer's human-verified concepts, main stayed red at lint `--strict` between the two merges. With both on main at `e759f5d`, the agent showed the two rows and asked in the session's question tool. Kept verbatim.

**Question** (header "scripts-okf")

> Do you verify 'OKF scripts' (knowledge/base/systems/scripts-okf.md) at generated.at 2026-11-12T04:06:05Z, commit e759f5d? Since your verification of 2026-11-11 only two rows changed. okf_index.py adds: 'lists each kind's instances with their state in the kind directory's index, under the kind's description from the Domain Profile' (okf-3vg.3, #101). okf_migrate.py replaces 'together with a root directory that holds nothing else' with: 'keeps a root directory at the root only when it holds operational instances (nested bundles whose root index.md declares a kind) and no other document besides its index.md (a kind's directory of instances); it moves a root directory holding only ignored paths or nested bundles without kind under base/ with them' (okf-3vg.9, #100).
>
> Options: "Verify" (I record your answer verbatim as a fragment (ADR-0033), the concept goes back to stable with your verification, and a docs PR turns main's lint --strict green again. Right if both rows read correctly to you.) · "Read it first" (You open the file on main and answer later. Main stays red at lint --strict on this one warning until you do. Right if you want to read the two rows inside their full table.) · "Change something" (Write in the note what doesn't fit. I fix it in a docs PR and ask again, and main stays red meanwhile. Right if either row describes the script wrongly.)

**Answer**: "Verify"

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Question | — | verified | [OKF scripts](/base/systems/scripts-okf.md) |
