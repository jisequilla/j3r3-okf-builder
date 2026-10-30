---
type: Runbook
title: {{title}}
description: {{one_sentence_description}}
resource: {{dashboard_or_alert_url}}
tags: [runbook, oncall, {{tags}}]
status: draft
owner: team:{{team}}
stale_after: {{iso_date}}
generated: { by: {{actor}}, at: {{now}} }
---

# Disparador

{{Alerta, síntoma o evento que activa este runbook. Enlaza al sistema: [X](/systems/x.md).}}

# Impacto

# Diagnóstico

1. Comprobar ...
2. ...

# Pasos de resolución

1. ...

# Rollback

# Escalado

| Nivel | Quién | Cuándo |
|---|---|---|

# Post-incidente

- Registrar en `log.md` y abrir ADR si procede.
