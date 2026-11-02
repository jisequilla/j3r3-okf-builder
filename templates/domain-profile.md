---
type: Domain Profile
title: Domain Profile of {{project}}
description: {{one_sentence_description}}
tags: [profile, taxonomy]
status: draft
extends: []                       # shared profiles, merged in order: /base/<path>.md or <repo-path>@<commit>; never a URL
types:                            # local types; a standard type gains fields only through a local type that extends it
  Client Meeting:
    extends: Knowledge Fragment   # a type of the built-in profile or of an extended profile
    description: A meeting with a client, recorded as it happened
    fields:                       # type: string | integer | boolean | date | datetime | date_or_datetime | actor | list (of) | enum (values) | path
      client: { type: string, level: warn, note: "The client's name as the contract writes it" }
      contract: { type: path, note: The concept of the contract the meeting is about }
families:                         # per directory under base/, written /base/<dir>/; covers its subdirectories
  /base/clients/:
    types: [Term, System, Architecture Decision, Open Question]   # the types allowed there; absent means any
    required: [tags]
forbidden: {}                     # key: { reason, level }, e.g. internal_notes: { reason: Internal notes stay out of the bundle, level: error }
fixed: {}                         # key: { value, level }, e.g. okf_lang: { value: en, level: warn }
by_type: {}                       # Type: { required, fixed, forbidden }, e.g. Policy: { required: [stale_after] }
rules:                            # { name, when: { field: value }, require: [fields], level }
  - { name: distilled-client-meeting-names-client, when: { type: Client Meeting, distillation_status: distilled }, require: [client], level: warn }
validator: []                     # run only with okf-lint --run-validators
# validator:
#   - { name: openapi, types: [API], command: "npx @redocly/cli lint" }
questions: []                     # the questions this bundle answers
# questions:
#   - { question: "Who owns each system?", field: System.owner }
#   - { question: "How is the product deployed?", concept: /base/architecture/deployment.md }
aliases: {}                       # optional local names
# aliases:
#   types: { Reunión con cliente: Client Meeting }
#   fields: { cliente: client }
#   values: [{ from: { ingerido: true }, to: { distillation_status: distilled } }]
generated: { by: {{actor}}, at: {{now}} }
sources: []
---

# What this bundle holds

{{What the bundle is about, how base/ is organised (by type, by domain, or both) and which shared profiles it extends.}}

# Types

## Client Meeting

{{Why the standard types do not fit as they are, and what this type adds to Knowledge Fragment. Cite in `sources` the fragment or decision where the need appeared.}}

- `client`: {{why the field exists and who fills it}}
- `contract`: {{why the field exists and who fills it}}
- Rule `distilled-client-meeting-names-client`: {{why a distilled meeting must name its client}}

# Families

## /base/clients/

{{What the directory holds, why only these types belong there, and why each requirement applies only there.}}

# Questions

{{The questions this bundle answers and where each answer lives. Map each one in `questions` when it is stable.}}
