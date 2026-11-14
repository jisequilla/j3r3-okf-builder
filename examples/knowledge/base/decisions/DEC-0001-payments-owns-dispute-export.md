---
type: Decision
title: "DEC-0001: The payments team owns the refund dispute export"
description: The payments team answers for the refund dispute export, and finance asks for a change to it by opening a Request.
tags: [decision, payments, finance]
status: draft
decision_id: DEC-0001
decision_status: accepted
supersedes:
superseded_by:
generated: { by: okf-builder/example, at: 2026-11-12T16:00:00Z }
sources:
  - { id: ownership-call, resource: /fragments/2026-11-12-dispute-export-ownership.md, title: "2026-11-12 · Payments-finance call: who owns the refund dispute export" }
---

# Context

Request req-0002 built the [refund dispute export](/base/domain/refund-dispute-export.md) for finance, and its closing made the export a term of the whole platform. Once the request closed, no team was named as answering for the export[^ownership-call].

# Decision

The payments team owns the refund dispute export: it builds the file and fixes it when a refund is missing from it[^ownership-call]. Finance asks for a change to the export by opening a Request, as it did with req-0002[^ownership-call].

# Alternatives considered

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| Finance owns the export | Its one reader answers for it | Finance cannot change the file by itself | Finance would still have to ask payments for every fix |

# Consequences

- Positive: a missing refund in the export has one team to go to.
- Negative / accepted debt: a new column waits for a Request, even a small one.

# Related

* [Refund dispute export](/base/domain/refund-dispute-export.md)

[^ownership-call]: 2026-11-12 · Payments-finance call: who owns the refund dispute export, Owner of the export and Changes to the export.
