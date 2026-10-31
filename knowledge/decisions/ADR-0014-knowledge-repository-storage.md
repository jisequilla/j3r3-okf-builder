---
type: Architecture Decision
title: "ADR-0014: A knowledge repository has one source, Git or SharePoint; other tools read it"
description: A team's knowledge bundle has exactly one editable copy, a Git repository by default or a SharePoint library for teams without Git; Microsoft 365, Google Drive and Obsidian read it, and the bundle starts as one monorepo with a stated rule for splitting by domain.
tags: [adr, storage, projections]
status: draft
adr_id: ADR-0014
decision_status: accepted
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
| Obsidian | no agent read path of its own; a vault is a folder | native; nested YAML (`generated: { by, at }`) shows as raw JSON rather than an editable property[^obsidian-properties], though Bases views can read it | none without a git plugin | resolves `/` links from the vault root; on rename it rewrites them without the leading `/`, breaking them, unless links are set to relative[^obsidian-links] |

Two things follow. Only Git gives review of a change as a diff, which the distillation step of [ADR-0012](/decisions/ADR-0012-knowledge-fragments-and-distillation.md) and the human-verification rule of [ADR-0005](/decisions/ADR-0005-required-generated-human-verified.md) rely on. And the M365 path the project assumed (publish `knowledge/` to a SharePoint library and it "is indexed as is"[^m365-export]) is not documented.

# Decision

1. **Each bundle has exactly one source, the only copy that is edited.** It is one of two kinds:
   - *A Git repository*, the default. Changes go through branches and pull requests, and `okf_lint` runs on the repository.
   - *A SharePoint document library*, for teams that work in Microsoft 365 without Git. The library holds the `knowledge/` folder as `.md` files. People and agents work on it through the OneDrive sync client, which makes it a local folder, so `okf_lint`, Claude Code and Cowork run on it unchanged. History is the library's version history. Because there is no diff review, each change set that `okf-distill` (ADR-0012) applies is approved in the conversation and recorded in `log.md`, which becomes the review trail.
2. **Every other tool reads the source, and none is edited:**
   - *Microsoft 365 Copilot*: for a Git source, the GitHub Cloud Knowledge connector on the repository; for a SharePoint source, the library itself, once a tenant test shows Copilot uses `.md` files there.
   - *Google Drive*: a scheduled job copies `knowledge/` to a Drive folder with `rclone`, for Gemini Notebook and Drive users.
   - *Obsidian*: a person opens the Git working copy or the OneDrive-synced folder as a vault, with the relative link format, so a rename leaves valid links (`.obsidian/app.json`: `useMarkdownLinks`, `newLinkFormat: relative`, `alwaysUpdateLinks`).
3. **Start with one knowledge monorepo.** Split into one repository per business domain when two domains define the same term differently, or when a domain needs its own access rules. Each domain repository then owns its concepts, and the others link to them by URL; how changes propagate between them is a later ADR.
4. **A bundle can move between kinds** by copying the folder: the files are the same in both.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Git only | One review flow (pull requests) for everyone | Teams without Git, such as Microsoft 365 shops, cannot keep a bundle | Excludes a real user's setup |
| Google Drive as a source | Simple sharing; Gemini Notebook reads `.md` | No review; binary-file history expires; no team in view needs it | Not needed yet; Drive stays a read copy |
| Obsidian Sync as a source | Good editor and graph view | No review, no read-only role, up to 20 users | A reading and editing tool on top of a source, not a source |
| Edit in several places, sync both ways | Each person uses their own tool | Two-way sync of text conflicts silently | Makes the bundle's history unreliable |
| One repository per domain from the start | Clear ownership | Cross-domain links and conflicts before anyone needs them | Premature; the split rule covers it |

# Consequences

- Positive: a team keeps its bundle where it already works; every bundle still has one history and one editable copy; agents on every platform read the same files.
- Negative / accepted debt: a SharePoint source has no diff review, only version history and the `log.md` trail; whether M365 Copilot reads `.md` from SharePoint is undocumented, so until a tenant test passes, a SharePoint bundle serves Claude and Cowork through the synced folder but may not serve M365 Copilot; the GitHub connector needs a Copilot licence or metered use and a GitHub-to-Entra identity mapping, and permission changes apply only at the next full crawl; Drive copies lag behind the source by the job's interval.
- Follow-up actions: run the tenant test with the M365 probe (does Copilot use `.md` in a SharePoint library; does the GitHub connector work); correct the SharePoint note in `tools/export_m365.py`; once accepted, runbooks for a SharePoint-source bundle and for the Drive copy job.

# Not verified

- Whether M365 Copilot uses `.md` files stored in SharePoint in practice.
- Whether the SharePoint and Drive Markdown viewers show, hide or break YAML frontmatter, and whether SharePoint's editor rewrites it.
- Whether Gemini Enterprise and the Gemini app read `.md` from Drive.

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
[^obsidian-links]: Obsidian community forum, June 2026; reproduced on 2026-10-31 by opening this repository's `knowledge/` as a vault and renaming an ADR: the default and `absolute` link formats left 2 and 5 broken links, the `relative` format none.
[^m365-export]: The SharePoint note near the end of `tools/export_m365.py`.
