---
type: System
title: OKF scripts
description: okf_init, okf_lint, okf_index and okf_migrate (Python ≥ 3.9, no dependencies) in okf-standard/scripts.
resource: /plugin/okf-builder/skills/okf-standard/scripts
tags: [system, scripts, python]
status: draft
owner: human:jisequilla
runtime: python3
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T23:20:46Z }
---

# Responsibility

| Script | Function | Output |
|---|---|---|
| okf_init.py | Scaffold of `knowledge/` (v0.2 or v0.1) | files; regenerates indexes |
| okf_lint.py | Spec conformance (§11) + profile; version detection | ERROR/WARN findings, `--json`, exit code |
| okf_index.py | Regenerates `index.md` per directory from frontmatter | `--check` for CI |
| okf_migrate.py | 0.1 ↔ 0.2, `--dry-run`, `--out`, `--keep-extensions`, `--file` | files + entry in log.md |
| okf_common.py | Reduced YAML parser, Doc model, version detection | library |

# Examples

```bash
python3 <skills>/okf-standard/scripts/okf_lint.py knowledge --strict
python3 <skills>/okf-standard/scripts/okf_migrate.py knowledge --to 0.2 --dry-run
```

# Operation

* Tests: `make test` (init 0.1/0.2, Google fixtures v0.1 and v0.2, migration round-trip).
* Decisions: [ADR-0006](/decisions/ADR-0006-dependency-free-scripts.md), [ADR-0004](/decisions/ADR-0004-dual-support-v01-v02.md).
