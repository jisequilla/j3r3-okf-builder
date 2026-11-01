---
type: System
title: okf-builder plugin
description: Package of 10 Agent Skills (okf-standard, init, capture, fragment, distill, review, lint, index, ask, migrate) that apply profile knowledge/2.0.
resource: /plugin/okf-builder
tags: [system, plugin, skills]
status: draft
owner: human:jisequilla
runtime: agent-skills
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T16:00:00Z }
---

# Responsibility

Give any agent the instructions to create, maintain, validate, query and migrate OKF bundles. It runs nothing by itself: it delegates to [the scripts](/systems/scripts-okf.md).

# Interfaces

| Skill | Typical triggers | Uses |
|---|---|---|
| okf-standard | "what is OKF", "which type do I use", "0.1 vs 0.2" | references/, templates/ |
| okf-init | "initialize OKF", "create knowledge" | okf_init.py |
| okf-capture | "document this decision", "create a runbook" | templates, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-fragment | "capture this meeting", "save this transcript" | templates/fragment.md, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-distill | "distill this fragment", "what does this meeting change" | concept templates, templates/conflict-log.md, okf_index.py, okf_lint.py, okf_migrate.py --file |
| okf-review | "double check", "resolve this conflict" | okf_index.py, okf_lint.py |
| okf-lint | "validate knowledge" | okf_lint.py |
| okf-index | "regenerate indexes" | okf_index.py |
| okf-ask | "why did we decide…?" | progressive reading of index.md |
| okf-migrate | "migrate to 0.2", "export for 0.1" | okf_migrate.py |

# Dependencies

* [OKF scripts](/systems/scripts-okf.md)
* Manifest: `plugin/okf-builder/.claude-plugin/plugin.json` (semver version; `marketplace.json` at the repo root).

# Operation

* Runbooks: [Publish a version](/runbooks/release-version.md)
* Validation: `claude plugin validate plugin/okf-builder/.claude-plugin/plugin.json`
