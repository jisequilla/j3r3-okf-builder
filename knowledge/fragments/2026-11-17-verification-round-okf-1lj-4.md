---
type: Knowledge Fragment
title: 2026-11-17 · Verification round okf-1lj.4 on the Knowledge Viewer
description: The owner's answers on the Knowledge Viewer to round okf-1lj.4, the first round built by okf_viewer.py and checked by okf_viewer.py --answers; the Knowledge Viewer, the runbook for a verification round, the OKF scripts and the okf-builder plugin confirmed at their current version and applied.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-17T20:57:16Z
origin: Knowledge Viewer, a Claude artifact private to human:jisequilla (https://claude.ai/artifact/Tuhiidxvb6RtxXEuUUzszE, page version 1794779520-2031)
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "e7257477ec04d0d122ca09f510fb389b82a2b704" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-17T20:58:43Z }
---

# Record

The round okf-1lj.4 was answered on the Knowledge Viewer, a review page private to the owner, under [SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md) decision 4. The page was built by `okf_viewer.py` at commit `e725747` from a clean tree (`page_built_at` 2026-11-15T21:51:52Z) with the round's four concepts and published on 2026-11-15T21:52:05Z. On 2026-11-17 the owner typed in the router session of this repository "done i have answer the questions", which the router passed to the worker session. The agent then read the answers stored after the round was published (collection `answers`, `answered_at` later than 2026-11-15T21:52:05Z: four documents; none with a later `commented_at`) and ran `okf_viewer.py knowledge --answers <export> --json --since 2026-11-15T21:52:05Z`, which gave four rows, each `APPLY`: confirmed at the concept's current `generated.at`, 2026-11-15T21:48:55Z.

The stored answers, as the page's store held them when read (one document per line, with its store id and version):

```json
{"id":"base~systems~knowledge-viewer.md","data":{"answered_at":"2026-11-17T20:53:27Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"e7257477ec04d0d122ca09f510fb389b82a2b704","generated_at":"2026-11-15T21:48:55Z","page_built_at":"2026-11-15T21:51:52Z","path":"/base/systems/knowledge-viewer.md","round":"okf-1lj.4"},"version":1}
{"id":"base~runbooks~run-a-verification-round.md","data":{"answered_at":"2026-11-17T20:56:50Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"e7257477ec04d0d122ca09f510fb389b82a2b704","generated_at":"2026-11-15T21:48:55Z","page_built_at":"2026-11-15T21:51:52Z","path":"/base/runbooks/run-a-verification-round.md","round":"okf-1lj.4"},"version":1}
{"id":"base~systems~scripts-okf.md","data":{"answered_at":"2026-11-17T20:57:01Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"e7257477ec04d0d122ca09f510fb389b82a2b704","generated_at":"2026-11-15T21:48:55Z","page_built_at":"2026-11-15T21:51:52Z","path":"/base/systems/scripts-okf.md","round":"okf-1lj.4"},"version":3}
{"id":"base~systems~plugin-okf-builder.md","data":{"answered_at":"2026-11-17T20:57:16Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"e7257477ec04d0d122ca09f510fb389b82a2b704","generated_at":"2026-11-15T21:48:55Z","page_built_at":"2026-11-15T21:51:52Z","path":"/base/systems/plugin-okf-builder.md","round":"okf-1lj.4"},"version":2}
```

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| Knowledge Viewer | — | verified | [Knowledge Viewer](/base/systems/knowledge-viewer.md) |
| Run a verification round | — | verified | [Run a verification round](/base/runbooks/run-a-verification-round.md) |
| OKF scripts | — | verified | [OKF scripts](/base/systems/scripts-okf.md) |
| okf-builder plugin | — | verified | [okf-builder plugin](/base/systems/plugin-okf-builder.md) |
