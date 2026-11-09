---
type: System
title: okf-builder plugin
description: Package of 11 Agent Skills (okf-standard, init, capture, fragment, distill, review, lint, index, ask, migrate, projection) and the knowledge-architect agent, which apply profile knowledge/3.0.
resource: /plugin/okf-builder
tags: [system, plugin, skills]
status: draft
owner: human:jisequilla
runtime: agent-skills
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:34:38Z }
---

# Responsibility

Give any agent the instructions to create, maintain, validate, query and migrate OKF bundles, and to check and refresh their projections. It runs nothing by itself: it delegates to [the scripts](/base/systems/scripts-okf.md).

# Interfaces

| Skill | Typical triggers | Uses |
|---|---|---|
| okf-standard | "what is OKF", "which type do I use", "0.1 vs 0.2" | references/, templates/ |
| okf-init | "initialize OKF", "create knowledge", "open the knowledge in Obsidian" | okf_init.py, okf_lint.py, okf_obsidian.py ([ADR-0032](/base/decisions/ADR-0032-obsidian-viewer-setup.md)) |
| okf-capture | "document this decision", "create a runbook" | templates, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-fragment | "capture this meeting", "save this transcript" | templates/fragment.md, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-distill | "distill this fragment", "what does this meeting change" | concept templates, templates/conflict-log.md, okf_index.py, okf_lint.py, okf_migrate.py --file, okf_projection.py --json |
| okf-review | "double check", "resolve this conflict" | okf_index.py, okf_lint.py, okf_audit.py |
| okf-lint | "validate knowledge" | okf_lint.py, okf_profile.py |
| okf-index | "regenerate indexes" | okf_index.py |
| okf-ask | "why did we decide…?" | progressive reading of index.md |
| okf-migrate | "migrate to 0.2", "export for 0.1" | okf_migrate.py |
| okf-projection | "create a projection", "refresh the projections", "which projections are stale" | okf_projection.py ([ADR-0031](/base/decisions/ADR-0031-projection-tools-transient-exception.md)) |

# Agent

`agents/knowledge-architect.md` is the [knowledge architect](/base/roles/knowledge-architect.md) as a plugin agent. It preloads all 11 skills, has no `tools` field, and its body names no Claude tools, so `just m365` can turn it into the M365 declarative agent, which carries the subset of at most 8 skills chosen in `build/m365-agent.json` ([ADR-0017](/base/decisions/ADR-0017-agent-skills-per-platform.md)).

# Dependencies

* [OKF scripts](/base/systems/scripts-okf.md)
* Manifest: `plugin/okf-builder/.claude-plugin/plugin.json` (semver version; `marketplace.json` at the repo root).

# Operation

* Runbooks: [Publish a version](/base/runbooks/release-version.md)
* Validation: `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json`
