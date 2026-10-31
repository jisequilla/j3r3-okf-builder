---
type: Architecture Decision
title: "ADR-0014: Git is the source of a knowledge repository; SharePoint, Drive and Obsidian read it"
description: A team's knowledge bundle lives in one Git repository, its only editable copy; Microsoft 365, Google Drive and Obsidian get read access or published copies, and the bundle starts as one monorepo with a stated rule for splitting by domain.
tags: [adr, storage, projections]
status: draft
adr_id: ADR-0014
decision_status: proposed
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-31T12:20:00Z }
sources:
  - { id: spec-git, resource: /references/okf-spec-google.md, title: "OKF v0.2 §3: a git repository is the recommended distribution" }
  - { id: cs-quotas, resource: "https://learn.microsoft.com/en-us/microsoft-copilot-studio/requirements-quotas", title: "Copilot Studio quotas and limits (SharePoint knowledge file types)" }
  - { id: semantic-index, resource: "https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot", title: "Semantic index for Copilot" }
  - { id: agent-builder, resource: "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/agent-builder-add-knowledge", title: "Agent Builder: add knowledge" }
  - { id: github-connector, resource: "https://learn.microsoft.com/en-us/microsoftsearch/github-cloud-knowledge-overview", title: "GitHub Cloud Knowledge connector for Microsoft 365" }
  - { id: sp-approval, resource: "https://support.microsoft.com/office/require-approval-of-items-in-a-list-or-library-cd0761c4-8c3f-4ea2-9435-13c28aa23d08", title: "SharePoint content approval" }
  - { id: sp-markdown, resource: "https://mc.merill.net/message/MC1261592", title: "Message Center MC1261592: Markdown in SharePoint and OneDrive (unofficial mirror)" }
  - { id: drive-markdown, resource: "https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html", title: "Markdown in Drive and Docs" }
  - { id: gh-plans, resource: "https://docs.github.com/en/get-started/learning-about-github/githubs-plans", title: "GitHub plans (protected branches on private repos)" }
  - { id: obsidian-properties, resource: "https://obsidian.md/help/properties", title: "Obsidian properties (no nested YAML)" }
  - { id: obsidian-links, resource: "https://forum.obsidian.md/t/rename-operations-should-preserve-link-prefix-style-for-updated-links/115472", title: "Obsidian forum: rename drops the leading / of links", author: "community forum" }
  - { id: m365-export, resource: tools/export_m365.py }
---

# Context

A team needs one place where its knowledge bundle lives. Four candidates came up: Git, SharePoint, Google Drive and Obsidian. What each offers, checked against the vendors' documentation on 2026-10-31:

| Backend | How agents read it | Markdown | Change review | Notes |
|---|---|---|---|---|
| Git (GitHub) | Claude Code, Copilot and Gemini read the files; M365 Copilot through the GitHub Cloud Knowledge connector, which indexes `.md` up to 30 MB and keeps GitHub permissions[^github-connector] | native | pull requests with required reviews; on private repos, protected branches need a paid plan[^gh-plans] | the spec's recommended distribution[^spec-git] |
| SharePoint | Copilot Studio, Agent Builder and the tenant index | rendered since 2026[^sp-markdown], but `.md` is not a documented type of SharePoint knowledge sources (DOCX, PPTX, PDF; Agent Builder adds TXT)[^cs-quotas][^semantic-index][^agent-builder] | version history; approval of whole files, no diff[^sp-approval] | |
| Google Drive | Gemini Notebook reads `.md` and resyncs Drive sources | rendered since October 2026[^drive-markdown] | revisions, no review | binary-file revisions expire after 30 days unless kept |
| Obsidian | no agent read path of its own; a vault is a folder | native, but nested YAML (`generated: { by, at }`) is not shown as properties[^obsidian-properties] | none without a git plugin | a reported bug drops the leading `/` of links on rename[^obsidian-links] |

Two things follow. Only Git gives review of a change as a diff, which the distillation step of [ADR-0012](/decisions/ADR-0012-knowledge-fragments-and-distillation.md) and the human-verification rule of [ADR-0005](/decisions/ADR-0005-required-generated-human-verified.md) rely on. And the M365 path the project assumed (publish `knowledge/` to a SharePoint library and it "is indexed as is"[^m365-export]) is not documented.

# Decision

1. **Git is the source.** A team's bundle lives in one Git repository, private or public by the team's choice. It is the only copy that is edited, through branches and pull requests, and `okf_lint` runs on it.
2. **Every other backend reads it, and none is edited:**
   - *Microsoft 365 Copilot*: the GitHub Cloud Knowledge connector on the repository, added as a knowledge source of the agent. Publishing to a SharePoint library is the fallback, only once a tenant test shows Copilot uses `.md` files there.
   - *Google Drive*: a CI job copies `knowledge/` to a Drive folder with `rclone` for Gemini Notebook and Drive users.
   - *Obsidian*: a person opens the Git working copy as a vault to read and browse it, and edits through Git, not Obsidian Sync.
3. **Start with one knowledge monorepo.** Split into one repository per business domain when two domains define the same term differently, or when a domain needs its own access rules. Each domain repository then owns its concepts, and the others link to them by URL; how changes propagate between them is a later ADR.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| SharePoint as the source | Where M365 users already work; no Git skills needed | No diff review; `.md` not a documented knowledge type; `okf_lint` needs a sync to run | Loses the review that distillation needs |
| Google Drive as the source | Simple sharing; Gemini Notebook reads `.md` | No review; binary-file history expires | Same as SharePoint, weaker history |
| Obsidian Sync as the source | Good editor and graph view | No review, no read-only role, up to 20 users; link-prefix bug | A reading tool, not a source |
| Edit in each backend, sync both ways | Each team uses its own tool | Two-way sync of text conflicts silently | Makes the bundle's history unreliable |
| One repository per domain from the start | Clear ownership | Cross-domain links and conflicts before anyone needs them | Premature; the split rule covers it |

# Consequences

- Positive: one history and one review flow for every change; agents on every platform read the same files; the M365 path no longer depends on an undocumented file type.
- Negative / accepted debt: people who do not use Git need help editing (the agents, or a web editor on GitHub); the M365 connector needs a Copilot licence or metered use and a GitHub-to-Entra identity mapping, and permission changes apply only at the next full crawl; Drive and SharePoint copies lag behind the repository by the sync interval.
- Follow-up actions: correct the SharePoint note in `tools/export_m365.py`; test the GitHub connector and SharePoint `.md` in a tenant (with the M365 probe); check Obsidian's link handling against this repo's bundle; once accepted, a runbook for the Drive copy job.

# Not verified

- Whether M365 Copilot uses `.md` files stored in SharePoint in practice.
- Whether the SharePoint and Drive Markdown viewers show, hide or break YAML frontmatter.
- Whether Gemini Enterprise and the Gemini app read `.md` from Drive.
- Whether Obsidian resolves `/`-prefixed links from the vault root (only forum reports).

# Related

* [ADR-0002: One bundle per repository in knowledge/](/decisions/ADR-0002-knowledge-folder-per-repo.md)
* [ADR-0007: Single source of skills and per-platform projections](/decisions/ADR-0007-single-source-and-projections.md)
* [ADR-0012: Knowledge fragments and distillation](/decisions/ADR-0012-knowledge-fragments-and-distillation.md)
* [Exporters](/systems/exporters.md)

[^spec-git]: OKF v0.2 §3, Bundle structure.
[^github-connector]: GitHub Cloud Knowledge connector overview.
[^gh-plans]: GitHub plans.
[^sp-markdown]: Message Center MC1261592, rollout April–May 2026, read through an unofficial mirror.
[^cs-quotas]: Copilot Studio quotas and limits.
[^semantic-index]: Semantic index for Copilot, supported file types.
[^agent-builder]: Agent Builder, add knowledge.
[^sp-approval]: SharePoint content approval.
[^drive-markdown]: Google Workspace Updates, 2026-10-05.
[^obsidian-properties]: Obsidian help, Properties.
[^obsidian-links]: Obsidian community forum, June 2026.
[^m365-export]: The SharePoint note near the end of `tools/export_m365.py`.
