---
type: System
title: Platform package exporters
description: build/export_copilot.py and build/export_m365.py generate the platform packages of the skills for other repos and for Microsoft 365 Copilot.
resource: /build
tags: [system, exporters, m365, copilot]
status: stable
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-fable-5-2, at: 2026-11-14T13:13:30Z }
verified: [{ by: human:jisequilla, at: 2026-11-09T10:56:45Z }, { by: human:jisequilla, at: 2026-11-14T13:20:25Z }]
---

# Responsibility

| Exporter | Output | For |
|---|---|---|
| export_copilot.py | `dist/copilot/.github/skills`, `.github/agents/okf.agent.md`, `AGENTS.okf.md` | Vendoring skills into another repo (Copilot, Claude, Gemini) |
| export_m365.py | `dist/m365/okf-builder-m365.zip` (manifest v1.28) and `dist/m365/skills/*.zip` | M365 Cowork plugin and per-skill upload in Copilot Studio / Agent Builder |
| export_m365.py | `dist/m365/okf-knowledge-architect-m365.zip` (manifest v1.28 + declarative agent v1.9) | The [knowledge architect](/base/roles/knowledge-architect.md) as an M365 declarative agent |

# Applicable rules

- They replace the `<skills>/` convention with the concrete path of the target.
- M365: each skill is self-contained and gets only the scripts and templates it uses (`NEEDS` table), to respect the limit of 20 companion files: `okf-init` the templates `okf_init.py` renders; `okf-capture` the 15 concept templates; `okf-fragment` `fragment.md`; `okf-distill` the concept templates except `decision.md` (14) and `conflict-log.md`; `okf-review` no templates. The M365 okf-standard keeps only `references/`, and its template table says each template is carried by the skill that writes that type. A template only one skill ships is named in `TEMPLATE_HOMES`, as `SCRIPT_HOMES` does for a script: `decision.md` goes in `okf-capture`, and the text of `okf-distill` and the Decision row of that table point to `okf-capture`'s copy. They add `license`/`metadata` and an environment note that matches what the skill ships, and the build fails if a skill's text names a script or template its copy does not carry. `okf-capture` and `okf-distill` both sit at the limit, and the `m365` step of `just test` checks that each carries exactly 20: a new template needs room made first.
- The knowledge-architect agent package is generated from `plugin/okf-builder/agents/knowledge-architect.md`: the body becomes `instructions`, and `build/m365-agent.json` gives the `agent_skills` and the conversation starters ([ADR-0017](/base/decisions/architecture/ADR-0017-agent-skills-per-platform.md)). Each configured skill is copied into the package, because `agent_skills` must point inside the same app package and an app carries one declarative agent. The exporter fails if the body passes 8,000 characters, or if the configured skills are empty, pass 8, repeat a skill, or name one the Claude agent does not list or the plugin does not have. It is a separate package with no app-level `agentSkills`, so it cannot break the Cowork plugin; whether one package can carry both is untested.
- The M365 manifests use stable GUIDs (uuid5 of the repo URL, one per package).
- The `copilot` step of `just test` exports the Copilot pack and checks that it carries every skill and that the `@okf` agent names each one; `build/check_skills.py` checks each `SKILL.md`, in the plugin and in the pack: frontmatter that parses, `name` equal to its directory within 64 characters, a `description` within 1,024 characters (1,536 with the name) and written in the third person outside quoted trigger phrases.

# Operation

* [Export and deliver platform packages](/base/runbooks/export-projections.md)
* Decision: [ADR-0007](/base/decisions/architecture/ADR-0007-single-source-and-projections.md)
