---
type: Project
title: OKF Builder
description: OKF standard (profile knowledge/2.0) and the okf-builder plugin for managing project knowledge with Claude, Copilot, M365 and Gemini
resource: https://github.com/jisequilla/j3r3-okf-builder
tags: [okf, knowledge, plugin]
status: draft
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T03:28:57Z }
---

# Purpose

Define a standard per-repository knowledge structure (`knowledge/`) based on Google's Open Knowledge Format, and deliver tools (skills + scripts) to create, maintain, validate and query it from any AI agent the team uses.

# Scope

- Includes: the standard (profile), templates, scripts run with uv (PEP 723), Agent Skills, projections for Claude Code, Claude Cowork, GitHub Copilot, Gemini CLI and Microsoft 365 Copilot, OKF v0.1 and v0.2 support.
- Excludes: serving or indexing bundles (consumers do that: Knowledge Catalog, SharePoint, search engines); running attested computations.

# Team and ownership

| Role | Person / team | Contact |
|---|---|---|
| Owner | human:jisequilla | jisequilla@gmail.com |

# Key links

| Resource | URL |
|---|---|
| Repository | https://github.com/jisequilla/j3r3-okf-builder |
| Upstream spec | https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf |

# Knowledge map

* [Architecture](/architecture/index.md) — single source and projections
* [Decisions](/decisions/index.md) — ADRs for the standard and the plugin
* [Domain](/domain/index.md) — OKF glossary
* [Systems](/systems/index.md) — plugin, scripts, exporters
* [Runbooks](/runbooks/index.md) — release, export, spec update
* [Policies](/policies/index.md) — rules every agent must follow in this repo
