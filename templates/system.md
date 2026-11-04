---
type: System
title: {{name}}
description: {{one_sentence_description}}
resource: {{repo_or_catalog_url}}
tags: [system, {{tags}}]
status: draft
owner: team:{{team}}
runtime: {{kubernetes|lambda|vm|...}}
generated: { by: {{actor}}, at: {{now}} }
---

# Responsibility

{{What it does and what it doesn't do.}}

# Interfaces

| Direction | Counterpart | Protocol | Contract |
|---|---|---|---|
| Exposes | | REST | {{a link to /base/apis/<name>.md}} |
| Consumes | | | |

# Dependencies

* {{Dataset: a link to /base/data/<name>.md}}
* {{System: a link to /base/systems/<name>.md}}

# Operation

* Runbooks: ...
* Dashboards: ...
* Alerts: ...

# Relevant configuration

| Variable | Description | Value per environment |
|---|---|---|
