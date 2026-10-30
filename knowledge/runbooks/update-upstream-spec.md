---
type: Runbook
title: Update the OKF spec from Google's upstream
description: What to do when GoogleCloudPlatform/knowledge-catalog publishes changes to okf/SPEC.md.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [runbook, spec, compatibility]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Trigger

A new version of `okf/SPEC.md` upstream (check quarterly, or when this runbook's `stale_after` has passed).

# Steps

1. Download `SPEC.md` and compare it with `okf-standard/references/OKF-SPEC-v<current>.md`.
2. Classify the changes: additive (new optional fields) vs breaking (renames, reserved names).
3. Update `references/` (verbatim copy + license), `OKF-COMPATIBILITY.md` (matrix) and, where applicable, `SUPPORTED_VERSIONS`, `V02_KEYS`/detection and `okf_migrate.py`.
4. Add an upstream fixture of the new version in `examples/fixtures/` and a case in `make test`.
5. A new ADR if the version policy changes ([ADR-0004](/decisions/ADR-0004-dual-support-v01-v02.md)).
6. Follow [Publish a version](/runbooks/release-version.md).
