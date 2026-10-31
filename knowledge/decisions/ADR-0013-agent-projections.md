---
type: Architecture Decision
title: "ADR-0013: One knowledge-architect agent source, projected to each platform's agent format"
description: The knowledge-architect agent is written once as a Claude plugin agent with only portable fields, and generated into the agent formats of GitHub Copilot, Gemini CLI, Microsoft 365 Copilot and OpenAI Codex; ChatGPT gets the skills only.
tags: [adr, projections, agents]
status: draft
adr_id: ADR-0013
decision_status: proposed
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

1. **The source is one Claude plugin agent**, `plugin/okf-builder/agents/knowledge-architect.md`. Claude's format is the richest of the Markdown ones, is GA, and VS Code reads it directly.
2. **The source uses only portable content**: `name`, `description`, a body written without platform-specific tool names, a list of the okf skills it works with, and a tool intent of read, write and execute. Any Claude-only field is kept out of the source.
3. **The body fits the smallest limit**: 8,000 characters, the M365 instructions cap, and at most 8 skills, the M365 `agent_skills` cap. The plugin has 7 skills today and `okf-distill` (ADR-0012) would make 8.
4. **Each projection is generated** by the existing exporters and `make` targets:
   - Claude Code and Cowork: shipped as is in the plugin.
   - GitHub Copilot: `make copilot` writes `.github/agents/knowledge-architect.agent.md`, mapping the tool intent to Copilot's aliases.
   - Gemini CLI: written to `.gemini/agents/` in the same pack.
   - Microsoft 365 Copilot: `make m365` adds a declarative agent JSON and `copilotAgents` to the package, with the body as `instructions` and the skills as `agent_skills`.
   - OpenAI Codex: a TOML file for `.codex/agents/`, with the body as `developer_instructions`; Codex becomes a new projection target of ADR-0007.
   - ChatGPT: no agent; it uses the skills.
5. **`skills:` is mapped per platform, not copied**: Claude preloads the listed skills; Codex and Copilot ignore the list, because the agent already sees every installed skill; M365 uses it as `agent_skills`.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| No agent; skills only (today) | Nothing new to project | The role and its judgment live nowhere; each platform improvises | The role is the point of the knowledge architect |
| Claude-only agent | One file, no generators | Copilot, Gemini, M365 and Codex users get no role | Contradicts the single-source, every-platform goal of ADR-0007 |
| A neutral canonical format (own YAML) generated into every platform, Claude included | No platform favoured | One more format to define and maintain; Claude loses direct editing and testing | Claude's format already covers the portable fields |
| Context-forked skills (`context: fork`) instead of an agent | No new file type | Gives isolation, not a role; Claude-only | Solves a different problem |

# Consequences

- Positive: one role definition reaches every platform that has agents; the persona cannot drift between copies; Codex joins the supported platforms.
- Negative / accepted debt: tool restriction is approximate outside Claude (Codex has none, M365 has capabilities, not tools); M365 forces the 8,000-character and 8-skill limits on every platform; Gemini CLI is a strategic risk, since the research found it replaced by Antigravity CLI for unpaid and Google One users from 2026-06-18, and whether Antigravity reads `.gemini/agents` is unverified.
- Follow-up actions: write the knowledge-architect profile in `knowledge/` first; once accepted, a layered build adding the agent source, the four generators and a `make test` check that every projection respects the limits; verify the items below.

# Not verified

- Whether the M365 package used for Cowork can carry a declarative agent alongside `agentSkills`.
- Whether Cowork honours `skills` and `model` in agent frontmatter.
- Whether Copilot's cloud agent and CLI honour `skills:`, and how VS Code maps Claude tool names.
- Whether Codex custom agents work in Codex cloud.
- Whether Antigravity CLI reads Gemini CLI's agent files.

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
