---
type: Standard Decision
title: "SDR-0027: A value alias's from and to are written in local names and resolved at load, it replaces every key of from but the type when to gives none, and a from that can never hold is invalid"
description: Once every layer of a Domain Profile is composed, the local field and type names in each value alias's from and to read as the declared ones; when the alias holds, each key of from is replaced by to except the type key, which stays unless to gives a type; a from or a to that names one key twice with different values once resolved is PROFILE_INVALID, and two aliases whose resolved from is equal are PROFILE_DUPLICATE_ID.
tags: [decision, standard, domain-profile, aliases]
status: stable
decision_id: SDR-0027
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-15T04:56:58Z }
verified: [{ by: human:jisequilla, at: 2026-11-15T04:59:07Z }]
sources:
  - { id: answers, resource: /fragments/2026-11-14-value-alias-from-and-to.md, title: "2026-11-14 · What a value alias's from and to may name, which keys of from it replaces, and a from that can never hold" }
  - { id: example, resource: /fragments/2026-11-15-verification-scripts-okf-056-15.md, title: "2026-11-15 · Verification of OKF scripts after okf-056.15, and SDR-0027 sent back for an example" }
  - { id: sdr-0019, resource: /base/decisions/standard/SDR-0019-built-in-domain-profile.md }
  - { id: standard, resource: plugin/okf-builder/skills/okf-standard/references/OKF-STANDARD.md, title: "OKF standard, §4.1 (the aliases key and What lint checks)" }
---

# Context

A Domain Profile gives local names to declared ones through `aliases`: `types` (`Norma: Standard Decision`), `fields` (`tipo: type`) and `values` (`{ from: { ingerido: true }, to: { distillation_status: distilled } }`)[^standard]. Lint and the skills resolve aliases first, so a local name gets the checks of what it stands for[^sdr-0019]. Since tracker item okf-056.10, a concept's frontmatter is resolved in a fixed order: local field names, then local type names, then value aliases, so a value alias is matched against declared names.

The alias's own `from` and `to` were still read as written, and the owner was asked what they should mean[^answers]. As written, they behave as follows:

* a `from { type: Norma }` holds for no spelling of the type, a `from { tipo: ... }` never holds, and a `from { ramo: legal }` with `fields { ramo: area }` never holds, because the concept's keys and type are already resolved when the alias is tested;
* a `to { type: Norma }` writes the local name back, so the type is no longer resolved;
* when the alias holds, every key of `from` is removed, so a `from` that names the type with a `to` that gives none leaves the concept with no type (`NO_TYPE`);
* a `from` that carries the type under both `tipo` and `type` with different values would, once resolved, collapse to one key, and nothing says so;
* `okf_obsidian.py` builds its view formulas from `from` as written.

## An example

A team writes its bundle in its own words and declares, in `base/profile.md`[^example]:

```yaml
aliases:
  types:  { Norma: Standard Decision }
  fields: { tipo: type, estado: decision_status }
  values:
    - { from: { estado: aceptada }, to: { estado: accepted } }             # (A) a Spanish value onto the enum
    - { from: { tipo: Norma, vigente: false }, to: { status: deprecated } } # (B) a norm no longer in force is deprecated
```

One of its concepts:

```yaml
tipo: Norma
estado: aceptada
vigente: false
```

Read with `from` and `to` as written, the concept's keys and type are resolved first (`type: Standard Decision`, `decision_status: aceptada`, `vigente: false`) and neither alias holds. (A) asks for `estado`, which is gone, so `decision_status` stays `aceptada`, a value outside its enum; the only spelling that holds, `from: { decision_status: aceptada }`, is written nowhere. (B) asks for `tipo` and `Norma`, both gone; spelled `from: { type: Standard Decision, vigente: false }` it holds, removes the type with the other keys of `from`, and leaves the concept with `NO_TYPE`, since its `to` gives none.

Under the decision below, (A) reads `from: { decision_status: aceptada }, to: { decision_status: accepted }` and (B) `from: { type: Standard Decision, vigente: false }, to: { status: deprecated }`, whatever the concept's spelling; both hold, (B) removes `vigente` and keeps the type, and the concept reads `type: Standard Decision`, `decision_status: accepted`, `status: deprecated`. An alias whose `to` gives a type still retypes the concept (`from: { tipo: Norma, clase: rara }, to: { type: Term }`). And two mistakes that were silent become findings at load: `from: { tipo: Norma, type: Policy }` asks for the type to be two things at once, and `from: { tipo: Norma }` beside `from: { type: Standard Decision }` are one alias written twice.

# Decision

1. **`from` and `to` are written in local names and resolved at load.** Once every layer of the Domain Profile is composed, each key of a value alias's `from` and `to` that is a local field name reads as the declared field, and a value under the type key that is a local type name reads as the declared type. `from { tipo: Norma }` is `from { type: Standard Decision }`, and `to { type: Norma }` gives `Standard Decision`. Every tool reads the resolved form, `okf_obsidian.py` included: its formulas test each key of `from` as the field is read through its local names.
2. **A value alias replaces every key of `from` but the type, unless `to` gives a type.** When the resolved `from` holds in full, each of its keys is removed and the keys of `to` are set, a key the concept also carries under its declared name keeping the concept's own value. The type key is removed only when `to` gives a type, so an alias that tests the type and sets another field leaves the type in place. `from { ingerido: true }` still removes `ingerido`.
3. **A `from` that can never hold is invalid.** A `from` or a `to` that, once resolved, names one key twice with different values (`from { tipo: Norma, type: Policy }`) is `PROFILE_INVALID`, naming the alias and both values. Two value aliases whose resolved `from` is equal are `PROFILE_DUPLICATE_ID`, compared in their resolved form, whatever the layers.
4. **It is a breaking change.** An alias that never held, because its `from` used a local name, starts holding: a concept it now matches can lose a field `to` does not give back, and a bundle that passed lint can fail it. The change is released as one.

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| `from` and `to` in declared names only, a local name in either a load-time finding | Nothing that passes lint starts to fail; no resolution at load | An author who writes the bundle in local names must switch to declared ones inside `aliases` alone | The owner chose local names, resolved at load[^answers] |
| Resolve `to` only, `from` declared-only with a finding | `to` can no longer un-resolve the type | Two rules for the two halves of one alias | Same answer |
| Keep removing every key of `from`, with a finding when `from` names the type and `to` gives none | One rule for every key | An alias that tests the type to set another field is refused | The owner chose to keep the type[^answers] |
| `from` as conditions only, nothing removed | No key is lost | `ingerido: true` stays beside `distillation_status: distilled`, and every existing value alias changes meaning | Same answer |
| A dead `from` as a warning, or no finding | Lint still passes without `--strict` | The alias silently does nothing | The owner chose `PROFILE_INVALID`[^answers] |

# Consequences

- Positive: a value alias means the same whichever names it is written in, as a concept's frontmatter already does; a `to` never un-resolves the type; an alias that tests the type keeps it; a contradictory alias is reported where it is written, at load.
- Negative / accepted debt: a bundle whose aliases used local names in `from` sees them start to hold, and may gain findings; two aliases that differ only in spelling become a duplicate.
- Follow-up actions: §4.1 of the standard states the rule; `okf_profile.py` resolves `from` and `to` at load, reports both findings and keeps the type in `resolve_aliases`; `okf_obsidian.py` builds its tests from the resolved `from`; a test per case; the [OKF scripts](/base/systems/scripts-okf.md) concept follows (tracker item okf-056.15).

# Related

* [SDR-0019: The standard's own types are a built-in Domain Profile](/base/decisions/standard/SDR-0019-built-in-domain-profile.md)
* [Domain Profile of okf-builder](/base/profile.md)

[^answers]: The owner's answers: "Local names, resolved at load", "All but the type" and "PROFILE_INVALID error".
[^example]: The worked example the owner asked for and asked to be added before verifying, kept in the verification fragment, "The explanation".
[^sdr-0019]: SDR-0019, decision 5: the tools read the profile, aliases resolved.
[^standard]: OKF standard, §4.1, the `aliases` key and "What lint checks": "Lint and the skills resolve aliases first, so a local name gets the checks of the type, field or value it stands for."
