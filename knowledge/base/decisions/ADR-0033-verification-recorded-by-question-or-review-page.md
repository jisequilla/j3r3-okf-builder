---
type: Architecture Decision
title: "ADR-0033: An agent writes a person's verification only from that person's recorded answer, given in a structured question or on a review page private to them, naming each concept and version"
description: Every concept carries generated and starts as a draft; verified with a human actor is written by the person, or by an agent from that person's recorded answer, given in the agent platform's question tool or on a review page private to the person that stores each answer with the concept's version, kept verbatim as a fragment and linked from the log.
tags: [adr, trust]
status: draft
adr_id: ADR-0033
decision_status: accepted
supersedes: /base/decisions/ADR-0025-verification-recorded-by-question.md
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-07T04:01:01Z }
sources:
  - { id: adr-0025, resource: /base/decisions/ADR-0025-verification-recorded-by-question.md }
  - { id: adr-0024, resource: /base/decisions/ADR-0024-fragment-capture-field-backfill.md }
  - { id: okf-12m, resource: "bead okf-12m", title: "Verification round: the policies and the accepted ADRs in force" }
  - { id: okf-1lj, resource: "bead okf-1lj", title: "Knowledge visualizer: browse the bundle and its graph on a web page" }
---

# Context

[ADR-0025](/base/decisions/ADR-0025-verification-recorded-by-question.md) lets an agent write a person's `verified` only from that person's answer to a structured question, "one the person answers by choosing an option or typing a reply in the agent platform's question tool", that names each concept by bundle path, repository commit and `generated.at`, kept verbatim as a fragment[^adr-0025].

The first verification round under it covers 22 concepts: the two policies and the 20 accepted ADRs in force[^okf-12m]. A question tool shows a few options at a time, without the concepts' text, so a person reviews each concept in another window and answers in batches. On 2026-11-07 the owner asked instead for a page on which to see every pending decision and answer as they read. That page is the start of the bundle viewer okf-1lj[^okf-1lj].

The owner chose, in answer to structured questions on 2026-11-07, a Claude artifact private to the person, with a first version holding an index, the concepts with their links, and a review view. A Claude artifact cannot write to the repository, so the page stores the answers and the agent applies them. That answer is not given in the question tool, so under ADR-0025 it would not count. The owner chose a new ADR that restates ADR-0025 with the page as a second channel and supersedes it.

What keeps the signal honest on the page is what keeps it honest in a question: the answer names what was reviewed and which version, only the named person can give it, and it is kept verbatim.

# Decision

1. **`generated: { by, at }` is required** in the profile (the spec leaves it optional). Actor: `human:<id>` if the person dictates the content, `okf-builder/<model>` if the agent synthesizes it.
2. **Every concept starts in `status: draft`.**
3. **`verified: { by: human:<id>, at }` records that the named person reviewed the concept as it stands at a named version.** Adding it moves the concept to `status: stable`. The person writes it, or an agent writes it under decision 4. No script adds `verified`, and approving a distillation change set never does ([ADR-0024](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)).
4. **An agent writes a person's verification only from that person's recorded answer**, given in one of two channels:
   - **A structured question**: the person answers by choosing an option or typing a reply in the agent platform's question tool, never inferred from the conversation.
   - **A review page private to the person**: a page that only the person's own account can answer on, such as a Claude artifact shared with nobody. It shows each concept's text with its bundle path and version, and it stores, per concept, the person's choice (confirm or not), the version shown and the time of the answer. The agent reads the stored answers only when the person asks it to, in the session.

   In both channels:
   - The answer names each concept by bundle path and its version: the repository commit and the concept's `generated.at`.
   - Only the person named in `by` answers; nobody verifies for someone else. A concept the person does not confirm, or rejects, stays unverified.
   - An answer whose `generated.at` is not the concept's current one is about an earlier version: the agent does not apply it, and the person is asked again.
   - The question and the answer, or the stored answers as the page holds them with the page's own version, are kept **verbatim as a Knowledge Fragment** (`okf-fragment`): `origin` the agent session or the page, `participants` the person and the agent, `occurred_at` the time of the answer. Its `# Distillation` lists each concept verified.
   - The agent then adds `verified: { by: human:<id>, at: <time of the answer> }` and `status: stable` to each confirmed concept, and a **Verification** entry in `log.md` that names the concepts and links the fragment.
   - A free chat reply does not count, and neither does approving a change set, nor an answer on a page that anyone but the person can answer on.
   - A concept edited after its verification keeps the gap as information (`generated.at` later than `verified.at`); to verify the new version, the person is asked again.
5. **A person may still write `verified` by hand**, as before; the commit records who did it.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Keep ADR-0025: the question tool only | One channel | A round of 22 concepts is answered in batches of a few, without their text | The owner asked for a page to review and answer on |
| A local viewer that writes `verified` itself, as a hand edit the person commits (decision 5) | No change to this decision; nothing leaves the machine | A local server to build and run | The owner chose a Claude artifact |
| A read-only page, answers in the question tool | ADR-0025 unchanged | Two places to work in | The owner chose answers on the page |
| The page builds the answer as text, pasted into the question tool's reply | ADR-0025 unchanged | A copy step per round | The owner chose answers stored on the page |
| Any page that can store answers | Simplest | Nothing ties the answer to the person | Only a page private to the person counts |

# Consequences

- Positive: a person reviews a round on one page with every concept's text and answers there; each agent-written `human:` entry still has a verbatim, dated record of who confirmed which version.
- Negative / accepted debt: the page channel depends on the platform keeping the page private to the person, which the bundle cannot check; with a Claude artifact, the concepts' text is copied to claude.ai; agents on platforms without such pages keep the question channel only.
- Follow-up actions: the standard's §6 "Human review" row (both copies), `okf-review` step 11, rule 4 of `AGENTS.md`, rule 6 of [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md), [Conformance with profile knowledge/3.0](/base/policies/okf-conformance.md), and the knowledge-architect agent name this ADR and the page channel; the okf-1lj review page; the okf-12m round through it.

# Related

* [ADR-0025: generated required, verification from a recorded question (superseded)](/base/decisions/ADR-0025-verification-recorded-by-question.md)
* [ADR-0024: Fragment record immutable, capture fields backfilled from it](/base/decisions/ADR-0024-fragment-capture-field-backfill.md)
* [Knowledge architect](/base/roles/knowledge-architect.md)
* [Rules for agents working in this repo](/base/policies/agents-in-this-repo.md)

[^adr-0025]: ADR-0025, decision 4.
[^okf-12m]: Bead okf-12m, description and notes.
[^okf-1lj]: Bead okf-1lj, notes of 2026-11-07.
