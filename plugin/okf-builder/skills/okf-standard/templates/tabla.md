---
type: Tabla
title: {{nombre}}
description: {{una_fila_por_...}}
resource: {{uri_tabla}}
tags: [datos, {{tags}}]
status: draft
owner: team:{{equipo}}
generated: { by: {{actor}}, at: {{ahora}} }
sources: []
---

# Schema

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | STRING | Identificador único. |

# Joins

Se une con [otra tabla](/datos/otra-tabla.md) por `clave`.

# Particionado y frescura

- Partición:
- SLA de frescura:

# Examples

```sql
SELECT ... FROM {{tabla}} WHERE ...
```
