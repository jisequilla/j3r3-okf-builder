---
type: Table
title: {{name}}
description: {{one_row_per_...}}
resource: {{table_uri}}
tags: [data, {{tags}}]
status: draft
owner: team:{{team}}
generated: { by: {{actor}}, at: {{now}} }
sources: []
---

# Schema

| Column | Type | Description |
|---|---|---|
| `id` | STRING | Unique identifier. |

# Joins

Joins with [other table](/data/other-table.md) on `key`.

# Partitioning and freshness

- Partition:
- Freshness SLA:

# Examples

```sql
SELECT ... FROM {{table}} WHERE ...
```
