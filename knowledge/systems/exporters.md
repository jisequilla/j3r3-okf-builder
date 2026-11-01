---
type: System
title: Projection exporters
description: tools/export_copilot.py and tools/export_m365.py generate the skill projections for other repos and for Microsoft 365 Copilot.
resource: /tools
tags: [system, exporters, m365, copilot]
status: draft
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T20:35:00Z }
---

# Responsibility

| Exporter | Output | For |
|---|---|---|
| export_copilot.py | `dist/copilot/.github/skills`, `.github/agents/okf.agent.md`, `AGENTS.okf.md` | Vendoring skills into another repo (Copilot, Claude, Gemini) |
| export_m365.py | `dist/m365/okf-builder-m365.zip` (manifest v1.28) and `dist/m365/skills/*.zip` | M365 Cowork plugin and per-skill upload in Copilot Studio / Agent Builder |
| export_m365.py | `dist/m365/okf-knowledge-architect-m365.zip` (manifest v1.28 + declarative agent v1.9) | The [knowledge architect](/roles/knowledge-architect.md) as an M365 declarative agent |

# Applicable rules

- They replace the `<skills>/` convention with the concrete path of the target.
- M365: each skill is self-contained and gets only the scripts and templates it uses (`NEEDS` table), to respect the limit of 20 companion files: `okf-init` the templates `okf_init.py` renders; `okf-capture` the 15 concept templates; `okf-fragment` `fragment.md`; `okf-distill` the concept templates and `conflict-log.md`; `okf-review` no templates. The M365 okf-standard keeps only `references/`, and its template table says each template is carried by the skill that writes that type. They add `license`/`metadata` and an environment note that matches what the skill ships, and the build fails if a skill's text names a script or template its copy does not carry. `okf-distill` sits at the limit: a new template needs room made first.
- The knowledge-architect agent package is generated from `plugin/okf-builder/agents/knowledge-architect.md`: the body becomes `instructions`, and `tools/m365-agent.json` gives the `agent_skills` and the conversation starters ([ADR-0017](/decisions/ADR-0017-agent-skills-per-platform.md)). Each configured skill is copied into the package, because `agent_skills` must point inside the same app package and an app carries one declarative agent. The exporter fails if the body passes 8,000 characters, or if the configured skills are empty, pass 8, repeat a skill, or name one the Claude agent does not list or the plugin does not have. It is a separate package with no app-level `agentSkills`, so it cannot break the Cowork plugin; whether one package can carry both is untested.
- The M365 manifests use stable GUIDs (uuid5 of the repo URL, one per package).

# Operation

* [Export and deliver projections](/runbooks/export-projections.md)
* Decision: [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md)
