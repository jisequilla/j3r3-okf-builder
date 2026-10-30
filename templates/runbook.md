---
type: Runbook
title: {{titulo}}
description: {{descripcion_una_frase}}
resource: {{url_dashboard_o_alerta}}
tags: [runbook, oncall, {{tags}}]
status: draft
owner: team:{{equipo}}
stale_after: {{fecha_iso}}
generated: { by: {{actor}}, at: {{ahora}} }
---

# Disparador

{{Alerta, síntoma o evento que activa este runbook. Enlaza al sistema: [X](/sistemas/x.md).}}

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
