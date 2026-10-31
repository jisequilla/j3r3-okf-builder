---
type: Architecture Decision
title: "ADR-0013: One knowledge-architect agent for Claude and Microsoft 365 Copilot"
description: The knowledge-architect agent is written once as a Claude plugin agent and generated into a Microsoft 365 Copilot declarative agent; other platforms keep using the skills until there is a need for their agent formats.
tags: [adr, projections, agents]
status: draft
adr_id: ADR-0013
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T12:05:00Z }
sources:
  - { id: claude-agents, resource: "https://code.claude.com/docs/en/sub-agents", title: "Claude Code subagents" }
  - { id: claude-plugins, resource: "https://code.claude.com/docs/en/plugins-reference", title: "Claude Code plugins reference" }
  - { id: cowork-support, resource: "https://claude.com/docs/plugins/platform-support", title: "Plugin support across Claude surfaces" }
  - { id: copilot-agents, resource: "https://docs.github.com/en/copilot/reference/custom-agents-configuration", title: "GitHub Copilot custom agents configuration" }
  - { id: vscode-agents, resource: "https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference", title: "VS Code custom agent file reference" }
  - { id: gemini-agents, resource: "https://geminicli.com/docs/core/subagents/", title: "Gemini CLI subagents" }
  - { id: m365-agent, resource: "https://learn.microsoft.com/en-us/microsoft-365-copilot/extensibility/declarative-agent-manifest", title: "M365 declarative agent manifest" }
  - { id: codex-agents, resource: "https://learn.chatgpt.com/docs/agent-configuration/subagents", title: "Codex subagents" }
  - { id: chatgpt-plugins, resource: "https://learn.chatgpt.com/docs/plugins", title: "ChatGPT plugins" }
  - { id: m365-export, resource: tools/export_m365.py }
---

# Context

The plugin ships skills only. The planned knowledge architect is a role, not a skill: it decides when to capture, distill, index or ask, and what to hand to a person. [ADR-0007](/decisions/ADR-0007-single-source-and-projections.md) keeps one source of skills and projects it to each platform, which works because every platform reads `SKILL.md`. Agents have no shared standard. The formats, checked against each platform's documentation on 2026-10-31:

| Platform | Agent file | Can use the okf skills | Tool restriction |
|---|---|---|---|
| Claude Code, Cowork | plugin `agents/*.md`, Markdown + frontmatter[^claude-agents][^claude-plugins] | `skills:` preloads them | tool names (`tools`, `disallowedTools`) |
| GitHub Copilot | `.github/agents/*.agent.md`, body ≤ 30,000 chars; VS Code also reads `.claude/agents/`[^copilot-agents][^vscode-agents] | skills work on every surface; `skills:` documented only in VS Code | aliases (`read`, `edit`, `search`, `execute`, ...) |
| Gemini CLI | `.gemini/agents/*.md`[^gemini-agents] | skills exist; no subagent `skills` field | tool list with wildcards |
| Microsoft 365 Copilot | declarative agent JSON (v1.9) referenced from the app manifest; instructions ≤ 8,000 chars, ≤ 8 skills[^m365-agent] | `agent_skills` | `capabilities`, `actions` |
| OpenAI Codex | TOML in `.codex/agents/`; `developer_instructions` holds the prompt[^codex-agents] | inherits the parent's skills | none; inherits the parent's sandbox |
| ChatGPT | no agent format; plugins carry skills, MCP and hooks, not agents[^chatgpt-plugins] | skills only | — |

Claude Cowork loads plugin agents; claude.ai Chat ignores them[^cowork-support]. The M365 package built today carries only app-level `agentSkills`[^m365-export].

# Decision

1. **Two platforms get the agent: Claude (Code and Cowork) and Microsoft 365 Copilot.** They are the platforms in use today. GitHub Copilot, Gemini CLI and OpenAI Codex are not implemented and stay open for a later ADR when someone needs them; their users keep the skills. ChatGPT has no agent format.
2. **The source is one Claude plugin agent**, `plugin/okf-builder/agents/knowledge-architect.md`, shipped as is in the plugin for Claude Code and Cowork.
3. **The source keeps to what M365 can carry**: `name`, `description`, a body without Claude tool names, and the list of okf skills it works with. The body stays within 8,000 characters and the list within 8 skills, the M365 caps. The plugin has 7 skills today and `okf-distill` (ADR-0012) would make 8.
4. **`make m365` generates the M365 agent** from the source: a declarative agent JSON referenced from `copilotAgents` in the package, with the body as `instructions` and the skill list as `agent_skills`.
5. **`skills:` means preload in Claude and `agent_skills` in M365.**

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| No agent; skills only (today) | Nothing new to project | The role and its judgment live nowhere; each platform improvises | The role is the point of the knowledge architect |
| Claude-only agent | One file, no generators | M365 users, the other platform in use, get no role | Leaves out a platform in use today |
| Every platform with an agent format (Copilot, Gemini, Codex too) | Same role everywhere | Three more generators and formats nobody uses yet; Gemini CLI is being replaced by Antigravity CLI | Not needed yet (YAGNI); the source format leaves the door open |
| A neutral canonical format (own YAML) generated into every platform, Claude included | No platform favoured | One more format to define and maintain; Claude loses direct editing and testing | Claude's format already covers the portable fields |
| Context-forked skills (`context: fork`) instead of an agent | No new file type | Gives isolation, not a role; Claude-only | Solves a different problem |

# Consequences

- Positive: one role definition for the two platforms in use; the persona cannot drift between them; one generator instead of four.
- Negative / accepted debt: M365 limits behaviour through capabilities, not tool names, so its agent is less restricted than Claude's; the M365 caps bind the Claude agent too; Copilot, Gemini and Codex users get no agent until a later ADR adds one.
- Follow-up actions: write the knowledge-architect profile in `knowledge/` first; once accepted, a layered build adding the agent source, the M365 generator and a `make test` check of the 8,000-character and 8-skill limits; verify the items below.

# Not verified

- Whether the M365 package used for Cowork can carry a declarative agent alongside `agentSkills`.
- Whether Cowork honours `skills` and `model` in agent frontmatter.

# Related

* [ADR-0007: Single source of skills and per-platform projections](/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0012: Knowledge fragments and distillation](/decisions/ADR-0012-knowledge-fragments-and-distillation.md)
* [Exporters](/systems/exporters.md)

[^claude-agents]: Claude Code subagents documentation.
[^claude-plugins]: Claude Code plugins reference: `agents/` directory and the `agents` key of `plugin.json`.
[^cowork-support]: Plugin support across Claude surfaces.
[^copilot-agents]: GitHub Copilot custom agents configuration.
[^vscode-agents]: VS Code custom agent file reference.
[^gemini-agents]: Gemini CLI subagents documentation.
[^m365-agent]: M365 declarative agent manifest, schema v1.9.
[^codex-agents]: Codex subagents configuration.
[^chatgpt-plugins]: ChatGPT plugins documentation.
[^m365-export]: `tools/export_m365.py` writes `agentSkills` and no `copilotAgents`.
