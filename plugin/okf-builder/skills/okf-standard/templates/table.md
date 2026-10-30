---
type: Table
title: {{name}}
description: {{una_fila_por_...}}
resource: {{table_uri}}
tags: [datos, {{tags}}]
status: draft
owner: team:{{team}}
generated: { by: {{actor}}, at: {{now}} }
sources: []
---

# Schema

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | STRING | Identificador único. |

# Joins

Se une con [otra tabla](/data/otra-tabla.md) por `clave`.

# Particionado y frescura

- Partición:
- SLA de frescura:

# Examples

```sql
SELECT ... FROM {{table}} WHERE ...
```
