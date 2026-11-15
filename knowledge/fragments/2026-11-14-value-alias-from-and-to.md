---
type: Knowledge Fragment
title: 2026-11-14 · What a value alias's from and to may name, which keys of from it replaces, and a from that can never hold
description: The owner's answers to three structured questions on the semantics of a value alias left open by the reverted fix round of okf-056.10, that from and to are written in local names and resolved at load, that every key of from is replaced except the type when to gives none, and that a from that can never hold is a PROFILE_INVALID error.
tags: [fragment, okf, domain-profile, aliases]
status: draft
occurred_at: 2026-11-14T22:06:34Z
origin: Claude Code session in this repository
participants: [human:jisequilla, okf-builder/claude-opus-5-5]
distillation_status: distilled
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-14T22:06:34Z }
---

# Record

## What the owner was asked

Tracker item okf-056.15 lists five consequences left open by the fix round of pull request #125 (okf-056.10), reverted in commit `db02b8f`. On main, a value alias is matched against the frontmatter after its local field names and local type names are resolved, while its own `from` and `to` are read as written: a `from { type: <local type name> }` holds for no spelling of a concept's type, a `from { <local name of the type key>: ... }` never holds, a `from` on another local field name (`fields { ramo: area }`, `from { ramo: legal }`) never holds, and a `to { type: <local type name> }` leaves the type unresolved. When the alias holds, every key of `from` is removed, so a `from` that names the type with a `to` that gives no type leaves the concept with `NO_TYPE`. A `from` carrying the type under both the local and the declared key with different values would, once resolved, collapse to one key. `okf_obsidian.py` builds its formulas from `from` as written.

## Which names from and to may use

Structured question, "okf-056.15 (1, 2, 4, 5): which names may a value alias's `from` and `to` use?", with the options:

1. Local names, resolved at load (recommended): once every layer is composed, local field and type names in `from` and `to` read as the declared ones. `from {tipo: Norma}` means `from {type: Standard Decision}`, and `to {type: Norma}` gives Standard Decision. Obsidian builds its formulas from the resolved `from`. Breaking: an alias that never held starts holding, e.g. `from {ramo: legal}` with `fields {ramo: area}`.
2. Declared names only: `from` and `to` must use declared names. A local field or type name in either one is a load-time finding naming the alias, because today it silently never holds.
3. Resolve `to` only: `to` is read through the local names, so it can't un-resolve the type. `from` stays declared-only, and a local name in it is a load-time finding.

The owner's answer: "Local names, resolved at load".

## Which keys of from are removed

Structured question, "okf-056.15 (1): today every key of `from` is removed when the alias holds, so `from {type: X}` with a `to` that gives no type leaves the concept with NO_TYPE. Which keys of `from` are removed?", with the options:

1. All but the type (recommended): every key of `from` is replaced by `to`, except the type key: that one stays unless `to` gives a type. `from {ingerido: true}` still drops `ingerido`.
2. All, plus a finding: keep removing every key. A `from` that names the type with a `to` that gives none is a load-time finding.
3. None (conditions only): `from` is only a test. Only the keys `to` names change, so `ingerido: true` stays on the concept beside `distillation_status: distilled`.

The owner's answer: "All but the type".

## A from that can never hold

Structured question, "okf-056.15 (3): a `from` that can never hold, e.g. the type under both `tipo` and `type` with different values, which collapse to one key once resolved. What does load report?", with the options:

1. PROFILE_INVALID error (recommended): load stops on it, naming the alias and the two values. The same goes for two aliases whose resolved `from` is equal (PROFILE_DUPLICATE_ID, keyed on the resolved form).
2. Warning: reported, but lint still passes without --strict.
3. Nothing: leave it as a dead alias, and document it in §4.1.

The owner's answer: "PROFILE_INVALID error".

# Distillation

| Item | Kind | Outcome | Concept |
|---|---|---|---|
| What the owner was asked | — | context | [SDR-0027](/base/decisions/standard/SDR-0027-value-alias-local-names.md) |
| Which names from and to may use | addition | applied | [SDR-0027](/base/decisions/standard/SDR-0027-value-alias-local-names.md) |
| Which keys of from are removed | addition | applied | [SDR-0027](/base/decisions/standard/SDR-0027-value-alias-local-names.md) |
| A from that can never hold | addition | applied | [SDR-0027](/base/decisions/standard/SDR-0027-value-alias-local-names.md) |
