---
type: Architecture Decision
title: "ADR-0004: Support OKF v0.1 and v0.2, with v0.2 as the default"
description: The profile writes v0.2, reads and validates v0.1, and migrates in both directions without mixing forms in a bundle.
tags: [adr, compatibility]
status: stable
adr_id: ADR-0004
decision_status: accepted
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Context

v0.2 (Jul 2026) introduced two breaking changes relative to v0.1: `timestamp` → `generated` and `# Citations` → `sources[]`. There are published v0.1 bundles and consumers that only understand v0.1. Details in [OKF-COMPATIBILITY](/references/okf-compatibility.md).

# Decision

- New bundle ⇒ v0.2. `okf-init --okf-version 0.1` only to interoperate with older consumers.
- A bundle's version = `okf_version` of the root `index.md`; if missing, a heuristic based on fields.
- Never mix forms; `okf-lint` flags it (`MIXED_VERSIONS`).
- Capture in the bundle's version, not in the preferred one.
- Downgrade to 0.1 only into a copy (`okf-migrate --to 0.1 --out`); the source stays on 0.2.

# Consequences

- Positive: Google's v0.1 bundles can be consumed, and bundles can be exported to older consumers without losing the source.
- Negative: the linter and the migrator have two modes to maintain; covered by `make test` with real fixtures of both versions.
