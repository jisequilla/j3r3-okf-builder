---
type: Sistema
title: {{nombre}}
description: {{descripcion_una_frase}}
resource: {{url_repo_o_catalogo}}
tags: [sistema, {{tags}}]
status: draft
owner: team:{{equipo}}
runtime: {{kubernetes|lambda|vm|...}}
generated: { by: {{actor}}, at: {{ahora}} }
---

# Responsabilidad

{{Qué hace y qué no hace.}}

# Interfaces

| Dirección | Contraparte | Protocolo | Contrato |
|---|---|---|---|
| Expone | | REST | [API](/apis/....md) |
| Consume | | | |

# Dependencias

* [Dataset](/datos/....md)
* [Sistema](/sistemas/....md)

# Operación

* Runbooks: [Incidente X](/runbooks/....md)
* Dashboards:
* Alertas:

# Configuración relevante

| Variable | Descripción | Valor por entorno |
|---|---|---|
