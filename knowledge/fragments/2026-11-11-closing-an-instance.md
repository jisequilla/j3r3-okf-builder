---
type: Knowledge Fragment
title: 2026-11-11 · Closing an instance, a script, a fragment in the parent and the carried state
description: The owner's answers, while the remaining okf-3vg tickets were being drafted, that closing an operational instance runs through a script okf_close.py that Microsoft 365 Copilot does not ship, that the closing fragment lives in the parent bundle, that an item carried up is marked with a new value carried, and that an instance concept edited after closing is reported by the audit; each against the agent's recommendation, and recorded in ADR-0039, which supersedes ADR-0038.
tags: [fragment, decision, bundles, standard]
status: draft
occurred_at: 2026-11-11T19:30:00Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
repository: { url: https://github.com/jisequilla/j3r3-okf-builder, commit: "f4ad8e9fa4c1d58aaa89d5bbe0205a4f6adc5a7e" }
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-11T19:37:52Z }
---

# Record

## The drafting

The owner chose to close the epic okf-3vg before merging release 0.11.0. Three agents drafted the tickets okf-4j8, okf-3vg.3, okf-3vg.5 and okf-3vg.6 against the code, read only, and the main session okf-3vg.4. They measured that `okf_index.py`, run on a domain bundle, rewrites each instance's root `index.md` without its frontmatter, so lint goes from 0 to 6 errors on one instance and to 22 on four; that lint accepts links from a bundle down into its instances, absolute and relative, and reports a link from an instance up to its parent as `LINK_OUTSIDE`; that `question_status: carried` is an error today; that the exported `okf-distill` for Microsoft 365 Copilot already ships 20 companion files, the limit; and that `okf_audit.py` does not look inside instances. The drafts left questions only the owner could decide, asked in structured questions, each option at the same depth (doctrine principle 13).

## The owner's answers

To "okf-3vg.5: ¿cómo se implementa el cierre de una instancia en okf-distill?", with the options text only in the skill (recommended), a read-only `--closing` report in lint, or a script `okf_close.py`, the owner wrote:

> script okf_close.py y m365 no lo lleva no vamos a hacer otra skill para esto m365 lo pierde.

To how the closing fragment links the promoted concepts in the parent, with the options a ledger convention without a lint change (recommended), lint accepting links into the parent, or the closing fragment living in the parent's `fragments/`, which contradicts ADR-0038 decision 7 and needs a new ADR: "Fragmento en el padre".

To how a question or conflict carried up to the parent is marked in the instance, with the options the existing values `dropped` and `resolved` with a reason (recommended), a new value `carried`, or `answered` with `answered_by`: "Nuevo valor 'carried'".

To where the check of a concept edited after `closed_at` lives, with the options a lint warning listed by okf-review (recommended), an `okf_audit` finding, or okf-review text only: "Hallazgo de okf_audit".

To how the change to ADR-0038 is recorded, with the options ADR-0039 replacing ADR-0038 as ADR-0023 and ADR-0037 did, a short ADR-0039 superseding only decisions 7 and 8, or a further round of questions before drafting: "ADR-0039 reemplaza a 0038".

To whether `okf_migrate`, which has the same gap as `okf_index`, enters okf-4j8, with the options out as a new bead, in whole, or a separate ticket in the same layer: "Ticket aparte en esta capa".

To how a kind directory's `index.md` lists its instances, with the options a state suffix like today's `_(draft)_`, a section per state, or a table: "Sufijo de estado".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| The drafting | — | context | no concept (measurements kept in the tickets of okf-4j8, okf-3vg.3, okf-3vg.5 and okf-3vg.6) |
| The owner's answers | Addition | applied | [ADR-0039](/base/decisions/ADR-0039-closing-operational-bundles.md) |
| The owner's answers | Deprecation | applied | [ADR-0038](/base/decisions/ADR-0038-domain-and-operational-bundles.md) |
