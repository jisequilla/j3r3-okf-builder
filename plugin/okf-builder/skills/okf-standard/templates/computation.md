---
type: Attested Computation
title: {{name}}
description: {{one_sentence_description}}
tags: [computation, {{tags}}]
status: draft
runtime: {{bigquery|postgres|dbt|python}}
parameters:
  - { name: {{param}}, type: {{string|integer|date}}, required: true }
executor:
  resource: /references/skills/{{run-on-x}}.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/{{sql_equality}}.py
stale_after: {{iso_date}}
generated: { by: {{actor}}, at: {{now}} }
sources: []
---

# Computation

```sql
SELECT ...
FROM ...
WHERE field = @{{param}}
```

Used by [the metric](/metrics/{{slug}}.md).
