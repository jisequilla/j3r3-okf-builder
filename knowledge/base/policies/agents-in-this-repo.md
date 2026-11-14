---
type: Policy
title: Rules for agents working in this repo
description: Obligations of any agent (Claude, Copilot, Gemini, M365) when modifying this repository; it is the normative content of AGENTS.md.
resource: /AGENTS.md
tags: [policy, agents]
status: stable
owner: human:jisequilla
stale_after: 2027-10-30T00:00:00Z
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T17:56:02Z }
verified: [{ by: human:jisequilla, at: 2026-11-07T08:30:40Z }, { by: human:jisequilla, at: 2026-11-08T14:12:07Z }, { by: human:jisequilla, at: 2026-11-08T21:39:09Z }, { by: human:jisequilla, at: 2026-11-09T01:20:11Z }, { by: human:jisequilla, at: 2026-11-14T16:21:34Z }]
---

# Rule

1. Read `knowledge/index.md` and the decisions before changing the standard, the skills or the scripts.
2. A decision change is a new decision that supersedes the previous one; history is never edited.
3. Edit only the source `plugin/okf-builder/skills/`; never the platform packages (`.claude/skills`, `.agents/skills`, `dist/`).
4. Finish with `just test` (code) and `just lint` (knowledge).
5. Do not use vendor variables in skills; use the `<skills>/` convention.
6. Add `verified: human:` only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and its version, kept as a fragment ([SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md)).
7. Google's specs in `references/` are verbatim copies (Apache-2.0): they are never edited; they are updated from upstream with [Update the OKF spec from Google's upstream](/base/runbooks/update-upstream-spec.md), and the update is recorded in `log.md`.
8. A pull request's title follows Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, `chore:`; `!` for a breaking change), then a sentence saying what changed, `feat`/`fix` for a change to the plugin (`plugin/okf-builder/`), text included, `docs` and the others for anything else, `!` when a bundle that passed lint would fail it; pull requests are squash-merged, so the title is the commit release-please reads ([DEC-0005](/base/decisions/DEC-0005-release-please.md)).

# Related

* [ADR-0007](/base/decisions/architecture/ADR-0007-single-source-and-projections.md) · [DEC-0001](/base/decisions/DEC-0001-dogfooding.md)
* [Building with agents](/base/doctrine/building-with-agents.md): the doctrine whose principles explain these rules and the runs that taught them
