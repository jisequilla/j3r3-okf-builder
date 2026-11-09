---
type: Runbook
title: Update the OKF spec from Google's upstream
description: What to do when GoogleCloudPlatform/knowledge-catalog publishes changes to okf/SPEC.md.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [runbook, spec, compatibility]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-11-08T21:34:38Z }
---

# Trigger

A new version of `okf/SPEC.md` upstream (check quarterly, or when this runbook's `stale_after` has passed).

# Steps

1. Download `SPEC.md` and compare it with `okf-standard/references/OKF-SPEC-v<current>.md`.
2. Classify the changes: additive (new optional fields) vs breaking (renames, reserved names).
3. Update `references/` (verbatim copy + license), `OKF-COMPATIBILITY.md` (matrix) and, where applicable, `SUPPORTED_VERSIONS`, `V02_KEYS`/detection and `okf_migrate.py`.
4. Add an upstream fixture of the new version in `examples/fixtures/` and a case in the `google-fixtures` step of `build/checks.py`.
5. A new ADR if the version policy changes ([ADR-0004](/base/decisions/ADR-0004-dual-support-v01-v02.md)).
6. Follow [Publish a version](/base/runbooks/release-version.md).

# Rollback

Each upstream update is its own PR. If it turns out wrong, revert that PR's merge: the `references/` copy, the compatibility matrix, the fixture and the code return together. Record the revert in `log.md`, naming the upstream commit that was undone. A version already released with it is fixed by a new release, following [Publish a version](/base/runbooks/release-version.md).
