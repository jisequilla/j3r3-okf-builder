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
| Exposes | | REST | [API](/base/apis/....md) |
| Consumes | | | |

# Dependencies

* [Dataset](/base/data/....md)
* [System](/base/systems/....md)

# Operation

* Runbooks: [Incident X](/base/runbooks/....md)
* Dashboards:
* Alerts:

# Relevant configuration

| Variable | Description | Value per environment |
|---|---|---|
