---
type: Policy
title: Rules for agents working in this repo
description: Obligations of any agent (Claude, Copilot, Gemini, M365) when modifying this repository; it is the normative content of AGENTS.md.
resource: /AGENTS.md
tags: [policy, agents]
status: stable
owner: human:jisequilla
stale_after: 2027-10-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T14:09:50Z }
verified: [{ by: human:jisequilla, at: 2026-11-07T08:30:40Z }, { by: human:jisequilla, at: 2026-11-08T14:12:07Z }]
---

# Rule

1. Read `knowledge/index.md` and the ADRs before changing the standard, the skills or the scripts.
2. A decision change is a new ADR that supersedes the previous one; history is never edited.
3. Edit only the source `plugin/okf-builder/skills/`; never the platform packages (`.claude/skills`, `.agents/skills`, `dist/`).
4. Finish with `make test` (code) and `make lint` (knowledge).
5. Do not use vendor variables in skills; use the `<skills>/` convention.
6. Add `verified: human:` only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and its version, kept as a fragment ([ADR-0033](/base/decisions/ADR-0033-verification-recorded-by-question-or-review-page.md)).
7. Google's specs in `references/` are verbatim copies (Apache-2.0): they are never edited; they are updated from upstream with [Update the OKF spec from Google's upstream](/base/runbooks/update-upstream-spec.md), and the update is recorded in `log.md`.

# Related

* [ADR-0007](/base/decisions/ADR-0007-single-source-and-projections.md) · [ADR-0008](/base/decisions/ADR-0008-dogfooding.md)
* [Building with agents](/base/doctrine/building-with-agents.md): the doctrine whose principles explain these rules and the runs that taught them
