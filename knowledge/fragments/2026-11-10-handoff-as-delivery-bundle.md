---
type: Knowledge Fragment
title: 2026-11-10 · A delivery is an operational bundle, its handoff a deliverable projection, and tickets are proposed from it like a distillation
description: The owner's discussion with the agent, after reviewing another bundle's delivery-1 acceptance criteria, on handoffs and spec-driven development from the knowledge; a delivery becomes an operational bundle holding its specs and its handoff, decisions return as its fragments, the tracker enforces and never mirrors state, and okf-builder proposes tracker tickets from a handoff for a person to approve.
tags: [fragment, decision, handoff, delivery, tracker]
status: draft
occurred_at: 2026-11-10T23:31:42Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: pending
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "d6957d170122ddaf4a7b37087c10d8228d446f85" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-10T23:31:42Z }
---

# Record

## Context

Another bundle of the owner's, which models its deliveries to implementers with requirements and acceptance criteria, sent this session its first delivery's criteria to challenge before projecting a handoff to okf-builder. The agent answered from okf-builder's side: four criteria contradict okf-builder today (a `canonical` projection of the example bundle cites drafts and `just test` expects it clean; a warning changes the exit code under `--strict`; Spanish section headings in a template okf-builder would ship, against [ADR-0010](/base/decisions/ADR-0010-english-canonical-profile-2.md); `okf-standard/templates/` holds concept templates only), several are untestable as written (no tool reads a projection's content, a channel only one platform has, no place to record a blocking decision or a confirmed level), and the changes that bring the method into okf-builder need an ADR here first. In that bundle, a handoff is a `composed`, `deliverable` projection, one per delivery, with fixed sections; decisions return through a "decision port" with several channels.

## The discussion

The owner asked, in their words:

> before we start the next work, let's discuss about the handoff concept and spec driven development from the knowledge, what do you think?

The agent answered that the approach inverts spec-driven development: the knowledge is the source and the spec a projection of it, so a handoff cites rather than invents, an uncitable claim becomes an open question before building, drafts are allowed but block the merge, and decisions return as fragments. It pushed back on four points: a delivery is a unit of work that opens, runs and closes, which is an operational bundle ([ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md)) rather than a lone projection; acceptance criteria need the way they are checked (automated, lint, manual) and where, not only a description; the implementer's challenge of the criteria before projecting is a step of the method; and okf-builder ships the generic mechanics (projection templates, a draft-ref warning, operational bundles, fragments from structured answers) while the method itself (impact levels, the two modes of the decision port, the handoff's sections) stays in the bundle that defines it.

The owner then said:

> so if i understand correctly instead of beign a projection is an Operation Bounded concept, so specs will like in the knwoledge but not the knowledge base, i think i like this approach, so base knowledge of the project would be on the base and the delivery part will have the specs and insided the specs a projection let's say canoncial projection would be the handoff is that it?

The agent corrected two points and raised one gap. A delivery is an operational bundle, an instance of a kind such as `Delivery` in `knowledge/deliveries/<id>/`, not a concept: its `fragments/` hold the questions and answers and the decisions returned, its `base/` the specs (requirements and acceptance criteria), its `projections/` the handoff. The handoff is `deliverable`, not `canonical`: it is sent, and each version records to whom. It asked whether requirements belong to the delivery, shaped there and promoted to the domain bundle when it closes, or to the product from the start, recommending the first. The gap: a projection's `refs` reach only its own bundle's `/base/`, so a handoff in a delivery cannot cite the domain's decisions and policies.

The owner asked:

> ok so what about beads or ticketing system, where do they came into place?

The agent answered that the tracker sits beside the knowledge, as the standard's routing already says (an action item goes to the team's tracker; the base never copies it, and a concept may link it): the knowledge holds what and why, the tracker who does what and its status, the code how. One delivery maps to one epic in the implementer's own tracker; links point from ticket to knowledge (the acceptance criterion's path and the handoff version), and the delivery's `project.md` may link the epic. A blocking decision becomes a blocked ticket, the tracker being the mechanism that stops the work, while its answer is captured as a fragment in the delivery bundle. States are never synced: done tickets are a signal, but a delivery closes by distilling. The tracker stays swappable. It asked whether okf-builder should help turn a handoff into tickets.

The owner answered:

> proposed and approved, like distillation

and, on recording this discussion here and in the other bundle:

> yes, do both, but the kdd-knowledge part needs to be done in it session repo.

# Distillation

Pending: each item waits for the ADR that decides it in okf-builder (AGENTS.md rule 1). Tracked as okf-jel (tickets proposed from a handoff, approved by a person) and okf-waq (projection refs into the parent bundles of an operational bundle). Still open: whether a delivery's requirements are promoted to the domain bundle when it closes or live there from the start, and whether acceptance criteria gain a field for how they are checked. The other bundle records its own part, superseding its handoff and decision-port decisions, in its own repository.
