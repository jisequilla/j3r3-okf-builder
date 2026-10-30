---
type: Policy
title: Rules for agents working in this repo
description: Obligations of any agent (Claude, Copilot, Gemini, M365) when modifying this repository; it is the normative content of AGENTS.md.
resource: /AGENTS.md
tags: [policy, agents]
status: draft
owner: human:jisequilla
stale_after: 2027-10-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Rule

1. Read `knowledge/index.md` and the ADRs before changing the standard, the skills or the scripts.
2. A decision change is a new ADR that supersedes the previous one; history is never edited.
3. Edit only the source `plugin/okf-builder/skills/`; never the projections (`.claude/skills`, `.agents/skills`, `dist/`).
4. Finish with `make test` (code) and `make lint` (knowledge).
5. Do not use vendor variables in skills; use the `<skills>/` convention.
6. Do not add `verified: human:` without the person's confirmation ([ADR-0005](/decisions/ADR-0005-required-generated-human-verified.md)).

# Related

* [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md) · [ADR-0008](/decisions/ADR-0008-dogfooding.md)
