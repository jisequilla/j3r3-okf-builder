---
type: Project
title: OKF Builder
description: OKF standard (profile knowledge/3.0) and the okf-builder plugin for managing project knowledge with Claude, Copilot, M365 and Gemini
resource: https://github.com/jisequilla/j3r3-okf-builder
tags: [okf, knowledge, plugin]
status: draft
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T18:23:39Z }
sources:
  - { id: conformance, resource: /base/policies/okf-conformance.md }
  - { id: dogfooding, resource: /base/decisions/DEC-0001-dogfooding.md }
  - { id: single-source, resource: /base/architecture/single-source-projections.md }
  - { id: verification, resource: /base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md }
  - { id: compatibility, resource: /base/references/okf-compatibility.md }
---

# Purpose

Define a standard per-repository knowledge structure (`knowledge/`) based on Google's Open Knowledge Format, and deliver tools (skills + scripts) to create, maintain, validate and query it from any AI agent the team uses. What happened is kept as it happened, becomes knowledge only when a person approves the change, and is trusted only once a person has verified it.

# Scope

- Includes: the standard (profile knowledge/3.0) with its built-in Domain Profile and each bundle's own, templates, scripts run with uv (PEP 723), Agent Skills and the `knowledge-architect` agent, platform packages for Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot, OKF v0.1 and v0.2 support, migration between OKF versions and profiles, fragments and their distillation, knowledge projections, operational bundles and their closing, and the Obsidian viewer setup.
- Excludes: serving or indexing bundles (consumers do that: Knowledge Catalog, SharePoint, search engines); running attested computations; tracking work (an action item is handed to the team's tracker, never kept in the bundle).

# Success criteria

- Every bundle the plugin creates or touches passes `okf_lint --strict` in its declared OKF version and profile, this repo's own bundle included (`just lint`).[^conformance][^dogfooding]
- The same skills run on Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot from one source, and `just test` fails when a package or a root copy drifts from it.[^single-source]
- A concept is `stable` only when a named person verified the version shown, and that answer is kept as a fragment; an agent never marks its own work verified.[^verification]
- A bundle stays readable as Google's OKF v0.1 and v0.2: the upstream fixtures pass and the migration round-trips (`just test`).[^compatibility]

# Team and ownership

| Role | Person / team | Contact |
|---|---|---|
| Owner | human:jisequilla | jisequilla@gmail.com |

# Key links

| Resource | URL |
|---|---|
| Repository | https://github.com/jisequilla/j3r3-okf-builder |
| Releases | https://github.com/jisequilla/j3r3-okf-builder/releases |
| Upstream spec | https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf |

# Knowledge map

* [Architecture](/base/architecture/index.md) — single source and platform packages
* [Decisions](/base/decisions/index.md) — decisions on the standard, the architecture and how the repo works
* [Doctrine](/base/doctrine/index.md) — the principles of building with agents
* [Domain](/base/domain/index.md) — OKF glossary
* [Domain Profile](/base/profile.md) — the types and rules of this bundle
* [Policies](/base/policies/index.md) — rules every agent must follow in this repo
* [References](/base/references/index.md) — the standard, the compatibility matrix and the upstream spec
* [Roles](/base/roles/index.md) — the knowledge architect
* [Runbooks](/base/runbooks/index.md) — release, export, spec update, building in layers
* [Systems](/base/systems/index.md) — plugin, scripts, exporters

[^conformance]: [OKF conformance](/base/policies/okf-conformance.md).
[^dogfooding]: [DEC-0001](/base/decisions/DEC-0001-dogfooding.md).
[^single-source]: [Single source and per-platform packages](/base/architecture/single-source-projections.md).
[^verification]: [SDR-0022](/base/decisions/standard/SDR-0022-verification-recorded-by-question-or-review-page.md).
[^compatibility]: [OKF compatibility](/base/references/okf-compatibility.md).
