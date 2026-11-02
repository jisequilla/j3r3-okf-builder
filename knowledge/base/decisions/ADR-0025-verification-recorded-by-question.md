---
type: Architecture Decision
title: "ADR-0025: generated is required, and an agent writes a person's verification only from that person's recorded answer to a question naming each concept and version"
description: Every concept carries generated and starts as a draft; verified with a human actor is written by the person, or by an agent after that person answers a structured question naming each concept and its version, kept verbatim as a fragment and linked from the log.
tags: [adr, trust]
status: draft
adr_id: ADR-0025
decision_status: accepted
supersedes: /base/decisions/ADR-0005-required-generated-human-verified.md
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-02T11:58:18Z }
sources:
  - { id: adr-0005, resource: /base/decisions/ADR-0005-required-generated-human-verified.md }
  - { id: adr-0024, resource: /base/decisions/ADR-0024-fragment-capture-field-backfill.md }
  - { id: kdd-pr, resource: "https://github.com/jisequilla/kdd-knowledge/pull/10", title: "KDD bundle: the human-validation policy asks the person through a question" }
---

# Context

[ADR-0005](/base/decisions/ADR-0005-required-generated-human-verified.md) made `generated` required and kept `verified` for people: "No skill or script adds `verified`. Only after the person's explicit confirmation is `verified: { by: human:<id>, at }` added"[^adr-0005]. The knowledge-architect agent reads that as "never write `verified` with a `human:` actor". The signal it protects is OKF's derived trust: any `human:` entry raises a concept to *human-reviewed*.

In practice the person who verifies is often in a session with an agent, and the agent does the editing. The person then has to write the frontmatter by hand, or the agent writes it from a chat reply that nobody can trace afterwards. The KDD bundle met both problems and changed its validation policy: the agent asks the person a question that names each concept and its version, keeps the question and the answer as a fragment, and writes `verified` from that answer[^kdd-pr]. Its agent now does what this profile forbids, and the bundle's owner, who also owns this profile, asked for the profile to allow it.

The question is what keeps the signal honest when the agent writes it. A free chat reply ("ok", "looks good") does not say what was reviewed or which version. A structured question that names the concepts and their versions does, and its verbatim record lets anyone check later who answered what.

# Decision

1. **`generated: { by, at }` is required** in the profile (the spec leaves it optional). Actor: `human:<id>` if the person dictates the content, `okf-builder/<model>` if the agent synthesizes it.
2. **Every concept starts in `status: draft`.**
3. **`verified: { by: human:<id>, at }` records that the named person reviewed the concept as it stands at a named version.** Adding it moves the concept to `status: stable`. The person writes it, or an agent writes it under decision 4. No script adds `verified`, and approving a distillation change set never does ([ADR-0024](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)).
4. **An agent writes a person's verification only from that person's recorded answer:**
   - The agent asks a **structured question**, one the person answers by choosing an option or typing a reply in the agent platform's question tool, never inferred from the conversation. It names each concept by bundle path and its version: the repository commit and the concept's `generated.at`.
   - Only the person named in `by` answers it; nobody verifies for someone else. A concept the person does not confirm, or rejects, stays unverified.
   - The question and the answer are kept **verbatim as a Knowledge Fragment** (`okf-fragment`): `origin` the agent session, `participants` the person and the agent, `occurred_at` the time of the answer. Its `# Distillation` lists each concept verified.
   - The agent then adds `verified: { by: human:<id>, at: <time of the answer> }` and `status: stable` to each confirmed concept, and a **Verification** entry in `log.md` that names the concepts and links the fragment.
   - A free chat reply does not count, and neither does approving a change set.
   - A concept edited after its verification keeps the gap as information (`generated.at` later than `verified.at`); to verify the new version, the person is asked again.
5. **A person may still write `verified` by hand**, as before; the commit records who did it.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0005: only the person writes `verified` | The strongest separation | The person edits frontmatter by hand, or the agent writes it from an untraceable chat reply | A recorded answer is traceable, and the KDD agent already works this way |
| Accept a chat confirmation | No new step | The reply says neither which concepts nor which version, and nothing records it | The question must name what is verified |
| Name the question tool of one platform (AskUserQuestion) | Matches the KDD policy word for word | Ties the standard to one vendor; other agents have their own tools (AGENTS.md rule 5) | The rule names what the question must contain, not the tool |
| Record the answer only in `log.md` | No fragment | The log is a summary; the answer would not be kept verbatim | The fragment is the record, the log links it |

# Consequences

- Positive: an agent can carry a verification through without hand edits, and every agent-written `human:` entry has a verbatim, dated record of who confirmed which version; the KDD agent and this profile agree again.
- Negative / accepted debt: the trust signal now also depends on the fragment being kept honestly, which nothing checks yet; one more fragment per verification session.
- Follow-up actions: the standard's §6 "Human review" row (both copies); the knowledge-architect agent and `okf-review` (ask the question for the drafts awaiting verification, capture the fragment, write `verified` and the log entry); AGENTS.md rule 4 and the policy for agents in this repo; a lint or audit check that every **Verification** entry for an agent-written `human:` actor links a fragment (with okf-flz); cite the KDD fragment of this decision, pinned to a commit, once kdd-knowledge PR #10 merges. A verification level between draft and human, and role actors, stay open in the [migration-tool fragment](/fragments/2026-11-02-migration-tool-okf-review.md).

# Related

* [ADR-0005: generated required and verified only by people](/base/decisions/ADR-0005-required-generated-human-verified.md)
* [ADR-0024: Fragment record immutable, capture fields backfilled from it](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)
* [Knowledge architect](/base/roles/knowledge-architect.md)
* [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md)

[^adr-0005]: ADR-0005, decision 2.
[^kdd-pr]: KDD bundle, pull request 10: the validation policy, the knowledge architect role v1.3 and fragment rev-11.
