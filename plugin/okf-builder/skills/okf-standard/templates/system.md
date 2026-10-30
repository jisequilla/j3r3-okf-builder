---
type: System
title: {{name}}
description: {{one_sentence_description}}
resource: {{repo_or_catalog_url}}
tags: [sistema, {{tags}}]
status: draft
owner: team:{{team}}
runtime: {{kubernetes|lambda|vm|...}}
generated: { by: {{actor}}, at: {{now}} }
---

# Responsabilidad

{{Qué hace y qué no hace.}}

# Interfaces

| Dirección | Contraparte | Protocolo | Contrato |
|---|---|---|---|
| Expone | | REST | [API](/apis/....md) |
| Consume | | | |

# Dependencias

* [Dataset](/data/....md)
* [Sistema](/systems/....md)

# Operación

* Runbooks: [Incidente X](/runbooks/....md)
* Dashboards:
* Alertas:

# Configuración relevante

| Variable | Descripción | Valor por entorno |
|---|---|---|
