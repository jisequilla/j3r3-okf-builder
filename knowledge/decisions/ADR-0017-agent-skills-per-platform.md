---
type: Architecture Decision
title: "ADR-0017: The Claude agent preloads every skill it needs; the Microsoft 365 agent takes a configured subset"
description: The knowledge-architect agent is still written once as a Claude plugin agent and generated into a Microsoft 365 Copilot declarative agent, but only M365's caps bind M365; the Claude agent lists every skill the role uses, and tools/m365-agent.json picks the at most 8 skills the M365 agent carries.
tags: [adr, projections, agents]
status: draft
adr_id: ADR-0017
decision_status: accepted
supersedes: /decisions/ADR-0013-agent-projections.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-01T20:35:00Z }
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

[ADR-0013](/decisions/ADR-0013-agent-projections.md) wrote the knowledge-architect agent once, as a Claude plugin agent, and generated the Microsoft 365 Copilot declarative agent from it. To keep one file valid for both, it held the Claude agent to M365's caps: a body of at most 8,000 characters and at most 8 skills. The plugin now has 10 skills, and the agent preloads 8 of them because M365 cannot carry more[^m365-export]. Claude has no such cap. Each new skill, such as a knowledge audit, would have to push another skill out of the Claude agent, or wait for M365.

The agent formats, checked against each platform's documentation on 2026-10-31, have not changed:

| Platform | Agent file | Can use the okf skills | Tool restriction |
|---|---|---|---|
| Claude Code, Cowork | plugin `agents/*.md`, Markdown + frontmatter[^claude-agents][^claude-plugins] | `skills:` preloads them | tool names (`tools`, `disallowedTools`) |
| GitHub Copilot | `.github/agents/*.agent.md`, body ≤ 30,000 chars; VS Code also reads `.claude/agents/`[^copilot-agents][^vscode-agents] | skills work on every surface; `skills:` documented only in VS Code | aliases (`read`, `edit`, `search`, `execute`, ...) |
| Gemini CLI | `.gemini/agents/*.md`[^gemini-agents] | skills exist; no subagent `skills` field | tool list with wildcards |
| Microsoft 365 Copilot | declarative agent JSON (v1.9) referenced from the app manifest; instructions ≤ 8,000 chars, ≤ 8 skills[^m365-agent] | `agent_skills` | `capabilities`, `actions` |
| OpenAI Codex | TOML in `.codex/agents/`; `developer_instructions` holds the prompt[^codex-agents] | inherits the parent's skills | none; inherits the parent's sandbox |
| ChatGPT | no agent format; plugins carry skills, MCP and hooks, not agents[^chatgpt-plugins] | skills only | — |

Claude Cowork loads plugin agents; claude.ai Chat ignores them[^cowork-support].

# Decision

1. **Two platforms get the agent: Claude (Code and Cowork) and Microsoft 365 Copilot.** GitHub Copilot, Gemini CLI and OpenAI Codex stay open for a later ADR when someone needs them; their users keep the skills. ChatGPT has no agent format.
2. **The source is one Claude plugin agent**, `plugin/okf-builder/agents/knowledge-architect.md`, shipped as is in the plugin for Claude Code and Cowork.
3. **The Claude agent's `skills:` lists every skill the role uses**, with no cap. Adding a skill to the plugin and to this list needs no ADR.
4. **The body still keeps to what M365 can carry**, because it becomes the M365 instructions: no Claude tool names and at most 8,000 characters. It may name skills the M365 agent does not carry; its "When the environment is limited" section tells the agent to say which skill is missing and what it would have done.
5. **`tools/m365-agent.json` configures the M365 agent**: the skills it carries (`agent_skills`) and its conversation starters. `make m365` generates the declarative agent from the source and that file, with the body as `instructions`. The build fails if the configured skills pass 8, name a skill the Claude agent does not list, or name a skill the plugin does not have.
6. **`skills:` means preload in Claude and `agent_skills` in M365.** The M365 list is a subset of the Claude list.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0013: M365's caps bind the Claude agent | One list, nothing new to configure | Every new skill pushes another out of the Claude agent or waits for M365 | Claude has no cap; the limit belongs to one platform |
| A second key in the agent frontmatter (`m365-skills:`) | One file to read | A field Claude does not define, in a file Claude validates | The M365 choices belong with the M365 exporter |
| A hard-coded list in `tools/export_m365.py` | No new file | M365 choices mixed with build code; harder to see and change | A config file makes the subset easy to review and edit |
| Two agent sources, one per platform | Each platform free | The persona drifts between them | ADR-0013's reason for one source still holds |

# Consequences

- Positive: the Claude agent grows with the plugin; the M365 subset is one reviewed file; the persona is still written once.
- Negative / accepted debt: the M365 agent can do less than the Claude agent, and its instructions name skills it lacks; choosing the M365 subset is a judgment made each time a skill is added. M365 limits behaviour through capabilities, not tool names, so its agent is less restricted than Claude's. Copilot, Gemini and Codex users get no agent until a later ADR adds one.
- Follow-up actions: the Claude agent preloads all 10 skills, and `tools/m365-agent.json` keeps the 8 the M365 agent carried under ADR-0013; the exporter reads it and `make test` checks it; verify the items below.

# Not verified

- Whether the M365 package used for Cowork can carry a declarative agent alongside `agentSkills`.
- Whether Microsoft 365 accepts the generated agent package and runs its skills; no tenant with Copilot has been available.

# Related

* [ADR-0007: Single source of skills and per-platform projections](/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0013: One knowledge-architect agent for Claude and Microsoft 365 Copilot](/decisions/ADR-0013-agent-projections.md)
* [ADR-0016: Distillation adds refutation](/decisions/ADR-0016-refutation-as-a-distillation-kind.md)
* [Exporters](/systems/exporters.md)
* [Knowledge architect](/roles/knowledge-architect.md)

[^claude-agents]: Claude Code subagents documentation.
[^claude-plugins]: Claude Code plugins reference: `agents/` directory and the `agents` key of `plugin.json`.
[^cowork-support]: Plugin support across Claude surfaces.
[^copilot-agents]: GitHub Copilot custom agents configuration.
[^vscode-agents]: VS Code custom agent file reference.
[^gemini-agents]: Gemini CLI subagents documentation.
[^m365-agent]: M365 declarative agent manifest, schema v1.9.
[^codex-agents]: Codex subagents configuration.
[^chatgpt-plugins]: ChatGPT plugins documentation.
[^m365-export]: `tools/export_m365.py` before this decision: the agent's skills list was copied as is into `agent_skills` and checked against the cap of 8.
