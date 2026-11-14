---
type: Knowledge Fragment
title: "2026-11-14 · Verification of the agents policy after okf-056.7 in a structured question"
description: The structured question that asked the owner to verify the policy for agents in this repo after its rules 1 and 2 came to say decisions instead of ADRs, and the owner's answer confirming it at the version named.
tags: [fragment, verification, review]
status: draft
occurred_at: 2026-11-14T18:07:08Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-fable-5-2]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "da6bd67f28f4ed6ace80aabfe2176f40b715a680" }
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T18:07:28Z }
---

# Record

## The agents policy at commit da6bd67

Tracker item okf-056.7 (draft pull request #123) changed rule 1 of `AGENTS.md` to say decisions instead of ADRs, and the policy followed in two lines. Structured question:

> As human:jisequilla, do you verify /base/policies/agents-in-this-repo.md at commit da6bd67 (PR #123), generated.at 2026-11-14T17:56:02Z? Only two lines change: rule 1 "Read `knowledge/index.md` and the decisions before changing the standard, the skills or the scripts." (was "the ADRs") and rule 2 "A decision change is a new decision that supersedes the previous one; history is never edited." (was "a new ADR").

Options: "Verified" (described as: "I confirm the concept is correct in this version. Adds a verified entry and keeps the answer as a fragment on PR #123."), "Not confirmed" (described as: "No verified entry is added; PR #123 stays a draft. Use the note to say what should change."). The owner's answer: "Verified".

The concept's `generated.at` was 2026-11-14T17:56:02Z when the answer was applied.

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The agents policy at commit da6bd67 | — | verified | [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md) |
