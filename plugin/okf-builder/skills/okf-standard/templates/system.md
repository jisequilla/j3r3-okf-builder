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
| Exposes | | REST | [API](/apis/....md) |
| Consumes | | | |

# Dependencies

* [Dataset](/data/....md)
* [System](/systems/....md)

# Operation

* Runbooks: [Incident X](/runbooks/....md)
* Dashboards:
* Alerts:

# Relevant configuration

| Variable | Description | Value per environment |
|---|---|---|
