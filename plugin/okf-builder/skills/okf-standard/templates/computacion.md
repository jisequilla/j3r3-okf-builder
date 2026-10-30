---
type: Attested Computation
title: {{nombre}}
description: {{descripcion_una_frase}}
tags: [computacion, {{tags}}]
status: draft
runtime: {{bigquery|postgres|dbt|python}}
parameters:
  - { name: {{param}}, type: {{string|integer|date}}, required: true }
executor:
  resource: /references/skills/{{run-on-x}}.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/{{sql_equality}}.py
stale_after: {{fecha_iso}}
generated: { by: {{actor}}, at: {{ahora}} }
sources: []
---

# Computation

```sql
SELECT ...
FROM ...
WHERE campo = @{{param}}
```

Usada por [la métrica](/metricas/{{slug}}.md).
