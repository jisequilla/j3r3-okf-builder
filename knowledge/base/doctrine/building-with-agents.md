---
type: Doctrine
title: Building with agents
description: The principles by which this repo builds changes with agent workflows, each with why it holds and the run that taught it.
resource: /.claude/workflows/okf-layer-ticket.js
tags: [doctrine, agents, workflow, process]
status: draft
owner: human:jisequilla
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-05T04:25:13Z }
sources:
  - { id: adr-0009, resource: /base/decisions/ADR-0009-build-in-layers-and-tickets.md, title: "ADR-0009: Build multi-stage changes in layers and delegated tickets" }
  - { id: adr-0028, resource: /base/decisions/ADR-0028-where-things-go.md, title: "ADR-0028: Where things go" }
  - { id: runbook, resource: /base/runbooks/build-in-layers.md, title: Build a change in layers }
  - { id: s-a1, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A1 merged" }
  - { id: s-lost, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: Ticket files lost" }
  - { id: s-a2, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A2, first to third pre-flight" }
  - { id: s-a2b, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A2, second pre-flight" }
  - { id: s-sleep, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: Builder killed by sleep" }
  - { id: s-secret, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A2 review: a secret printed" }
  - { id: s-hollow, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A hollow comparison" }
  - { id: s-a3, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A3" }
  - { id: s-a4, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A4" }
  - { id: s-a5, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: A5" }
  - { id: s-branches, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: Branch hygiene" }
  - { id: s-release, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: v0.9.0" }
  - { id: s-owner, resource: /fragments/2026-11-04-audit-build-session.md, title: "2026-11-04 session: How the owner decided" }
---

# Principles

How to carry them out is the runbook [Build a change in layers](/base/runbooks/build-in-layers.md); the rules every agent obeys are the [agents policy](/base/policies/agents-in-this-repo.md). Each principle here says why it holds and which run taught it.

1. **The main session judges and does not implement.** Builders work in their own worktrees and open draft PRs; fresh-context reviewers read only the PR; the main session verifies, asks the owner and merges. *Why:* a session that both builds and judges grades its own work, and loses half-done work to compaction[^adr-0009]. *Evidence:* in A5 the fresh-context review found four defects in the git-facts script the builder had delivered, and a separate fix agent corrected them[^s-a5].
2. **The ticket's text lives in the tracker**, never only in a session's scratch folder. *Why:* scratch folders are not kept. *Evidence:* the A2 ticket files were gone and were rebuilt from the beads, where their text had been stored[^s-lost].
3. **Measure a proposed check against the repo's own data before the ticket is written.** Run the idea over `knowledge/`, `examples/` and the fixtures and count what it would report. *Why:* a check specified in the abstract meets real data in the pre-flight, and each stop costs a round with the owner. *Evidence:* A2 needed four pre-flights: a secret pattern matching 176 ADR file names, checks firing on the repo's accepted ADRs, a verification older than a migration[^s-a2].
4. **Read the whole source before stating what it holds.** A claim about code or data names what was read. *Why:* a claim from a partial read is passed on as fact and is caught only by the next check, if any. *Evidence:* the agent said `mask_secrets` had token-prefix patterns and that every ledger row linked a concept; the pre-flights found neither was true[^s-a2b][^s-a4].
5. **An agent's report is a claim.** Verify on a fresh checkout of the pushed ref, and compare lint's `--json` between main and the PR. *Why:* the report may be wrong, truncated or about another state than what was pushed[^runbook]. *Evidence:* the main session's own comparison of lint output between main and a PR was wrong until it was redone[^s-hollow], and the A5 review found defects in what the builder had delivered[^s-a5].
6. **A check proves something only if it can fail.** Give every verification a case that must fail, or a control that must be found. *Why:* a comparison of two empty results says "same". *Evidence:* a comparison read the key `items`, which does not exist, and compared two empty lists[^s-hollow]; the secret-masking check counted the planted token three times in the source as its control[^s-secret]; the audit script was tried in a throwaway repository with cases that must report[^s-a5].
7. **Classify findings against the ticket's bar, not the reviewer's label.** *Why:* the bar was written before the review, with the owner; a reviewer's label was not. *Evidence:* a secret echoed by `BAD_STATUS` and `BROKEN_LINK` was labelled a fix, and was blocking because the bar named "a secret value printed anywhere"[^s-secret].
8. **Unattended runs need the machine awake, and interrupted work is kept.** Keep the machine awake for the length of the run; save an interrupted builder's work as a local WIP commit, resume the workflow from that branch so the cached pre-flight is reused, and squash before the PR. *Evidence:* the A2 builder died when the machine slept, with 25 files uncommitted[^s-sleep].
9. **An owner's decision is asked as a structured question, with a recommendation**, and settles only what it names; what a builder can settle from the context is written into the ticket instead. *Why:* a decision in a chat reply is easy to misread and leaves no record; a builder left to guess picks one reading silently. *Evidence:* A2's three rounds of owner questions[^s-a2]; in A3 the builder found the ticket inconsistent on `--no-profile` and took the consistent reading, which the agent then confirmed[^s-a3]; every decision of the session was asked this way[^s-owner].
10. **Irreversible and outward actions go through the owner's own words.** Merging, publishing a release and deleting remote branches are done on the owner's written instruction naming them, or by the owner. *Why:* they reach past the repo and cannot be taken back quietly. *Evidence:* the owner ran the remote branch deletions and named each merge and the release[^s-a1][^s-branches][^s-release].
11. **Check a release on a bundle outside the repo before announcing it.** *Why:* the repo's own bundles are kept clean, so they cannot show what an upgrade reports elsewhere. *Evidence:* the v0.9.0 notes missed `FRAGMENT_NO_LEDGER`, which another bundle reported 26 times on its first run[^s-release].

A principle that becomes a decision is an ADR, which this doctrine then links; a rule that comes out of it is added to the agents policy[^adr-0028].

# Related

* [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md)
* [Build a change in layers](/base/runbooks/build-in-layers.md)
* [ADR-0009: Build multi-stage changes in layers and delegated tickets](/base/decisions/ADR-0009-build-in-layers-and-tickets.md)
* [ADR-0028: Where things go](/base/decisions/ADR-0028-where-things-go.md)
* [2026-11-04 · Building the knowledge audit and v0.9.0 with agent workflows](/fragments/2026-11-04-audit-build-session.md)

[^adr-0009]: ADR-0009, Context and Decision.
[^adr-0028]: ADR-0028, decisions 7 and 8.
[^runbook]: Build a change in layers, Warnings.
[^s-a1]: The 2026-11-04 session, "A1 merged".
[^s-lost]: The 2026-11-04 session, "Ticket files lost".
[^s-a2]: The 2026-11-04 session, "A2, first pre-flight" to "A2, third pre-flight".
[^s-a2b]: The 2026-11-04 session, "A2, second pre-flight".
[^s-sleep]: The 2026-11-04 session, "Builder killed by sleep".
[^s-secret]: The 2026-11-04 session, "A2 review: a secret printed".
[^s-hollow]: The 2026-11-04 session, "A hollow comparison".
[^s-a3]: The 2026-11-04 session, "A3".
[^s-a4]: The 2026-11-04 session, "A4".
[^s-a5]: The 2026-11-04 session, "A5".
[^s-branches]: The 2026-11-04 session, "Branch hygiene".
[^s-release]: The 2026-11-04 session, "v0.9.0".
[^s-owner]: The 2026-11-04 session, "How the owner decided".
