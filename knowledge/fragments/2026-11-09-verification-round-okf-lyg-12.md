---
type: Knowledge Fragment
title: 2026-11-09 · Verification round okf-lyg.12 on the review page
description: The owner's answers on the private review page to round okf-lyg.12; ADR-0034, ADR-0035 and ADR-0036 confirmed at their current version and applied, and the confirmation of the agents policy kept but not applied, since the policy changed after it was given.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-09
origin: OKF Review Desk, a Claude artifact private to human:jisequilla (https://claude.ai/artifact/Tuhiidxvb6RtxXEuUUzszE, page versions 1794184711-eb44 and 1794186970-1dc0)
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "a0d54f7617dea9b748416654af8ea51c4bb8b82c" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-09T01:20:04Z }
---

# Record

The round okf-lyg.12 was answered on a review page private to the owner, under [ADR-0033](/base/decisions/ADR-0033-verification-recorded-by-question-or-review-page.md) decision 4. The page was first built at commit `0df7cb6` (2026-11-09T00:38:10Z) and rebuilt at `a0d54f7` (2026-11-09T01:16:00Z), after the owner decided that only a change to the plugin raises its version and that the marketplace manifest keeps its own; the rebuild changed ADR-0036 and the agents policy. On 2026-11-09 in the agent session the owner said "ok i confirm this round on the claude artifact". The agent then read the stored answers and compared each one's `generated_at` with the concept's: three match and are applied; the agents policy's answer was given for `generated.at` 2026-11-09T00:34:52Z, while the policy is at 2026-11-09T01:15:20Z, so it is kept here and not applied.

The stored answers, as the page's store held them when read (collection `answers`, one document per line):

```json
{"id":"base~decisions~ADR-0034-organization-package.md","data":{"answered_at":"2026-11-09T01:08:05Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"0df7cb67cd64f9df240333d003227bb8722c0f1b","generated_at":"2026-11-07T10:09:05Z","page_built_at":"2026-11-09T00:38:10Z","path":"/base/decisions/ADR-0034-organization-package.md","round":"okf-lyg.12"},"version":1}
{"id":"base~decisions~ADR-0035-just-build-runner.md","data":{"answered_at":"2026-11-09T01:03:27Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"0df7cb67cd64f9df240333d003227bb8722c0f1b","generated_at":"2026-11-08T21:33:29Z","page_built_at":"2026-11-09T00:38:10Z","path":"/base/decisions/ADR-0035-just-build-runner.md","round":"okf-lyg.12"},"version":1}
{"id":"base~decisions~ADR-0036-release-please.md","data":{"answered_at":"2026-11-09T01:19:06Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"a0d54f7617dea9b748416654af8ea51c4bb8b82c","generated_at":"2026-11-09T01:15:20Z","page_built_at":"2026-11-09T01:16:00Z","path":"/base/decisions/ADR-0036-release-please.md","round":"okf-lyg.12"},"version":1}
{"id":"base~policies~agents-in-this-repo.md","data":{"answered_at":"2026-11-09T00:52:34Z","by":"u_Kx3vJVI5SIVKP81e5LkuvQ","choice":"confirmed","commit":"0df7cb67cd64f9df240333d003227bb8722c0f1b","generated_at":"2026-11-09T00:34:52Z","page_built_at":"2026-11-09T00:38:10Z","path":"/base/policies/agents-in-this-repo.md","round":"okf-lyg.12"},"version":2}
```

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| ADR-0034 | — | verified | [ADR-0034](/base/decisions/ADR-0034-organization-package.md) |
| ADR-0035 | — | verified | [ADR-0035](/base/decisions/ADR-0035-just-build-runner.md) |
| ADR-0036 | — | verified | [ADR-0036](/base/decisions/ADR-0036-release-please.md) |
| Rules for agents working in this repo | — | not applied: answered for an earlier version | [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md) |
