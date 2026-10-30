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

# Trigger

{{Alert, symptom or event that starts this runbook. Link to the system: [X](/systems/x.md).}}

# Impact

# Diagnosis

1. Check ...
2. ...

# Resolution steps

1. ...

# Rollback

# Escalation

| Level | Who | When |
|---|---|---|

# Post-incident

- Record it in `log.md` and open an ADR if needed.
