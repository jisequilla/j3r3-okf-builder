---
type: Decision
title: "DEC-{{nnnn}}: {{title}}"
description: {{one_sentence_description}}
tags: [decision, {{tags}}]
status: draft
decision_id: DEC-{{nnnn}}
decision_status: proposed        # proposed | accepted | superseded | rejected
supersedes:                       # /base/decisions/DEC-XXXX-....md
superseded_by:
generated: { by: {{actor}}, at: {{now}} }
sources: []
---

{{How to write this concept: OKF-WRITING-GUIDE.md, in the okf-standard skill's references. Delete this line.}}

# Context

{{The forces that make a decision needed now, in one paragraph. Then a worked example, before and after. Not how the decision was reached: that is in the source fragment.}}

# Decision

{{What is decided, as numbered points, each one sentence a reader can act on.}}

# Alternatives considered

{{One row per option really weighed, with the reason it lost in a phrase.}}

| Alternative | Pros | Cons | Reason rejected |
|---|---|---|---|
| | | | |

# Consequences

{{What changes for the reader. One line each: positive, accepted debt, follow-up.}}

- Positive: ...
- Negative / accepted debt: ...
- Follow-up actions: ...

# Related

{{Links only, one per line.}}

* {{Affected system: a link to /base/systems/<name>.md}}
