---
type: Architecture Decision
title: "ADR-0006: Scripts Python sin dependencias externas"
description: Las herramientas (init, lint, index, migrate) son Python ≥ 3.9 sin pip; PyYAML se usa solo si está presente.
tags: [adr, tooling]
status: stable
adr_id: ADR-0006
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

Las herramientas deben correr en el sandbox de cualquier agente (Claude, Copilot, Gemini, M365) y en CI, donde no siempre hay red ni permisos para instalar paquetes.

# Decisión

Sin dependencias. `okf_common.py` incluye un parser YAML reducido para frontmatter OKF y usa PyYAML si existe. Los scripts se copian tal cual a `tools/okf/` de otros repos para CI.

# Consecuencias

- Positivas: ejecutables en cualquier sandbox; copiables.
- Negativas: el mini-parser no cubre YAML completo (anclas, multilínea `|`); suficiente para frontmatter OKF, y se prueba contra los bundles reales de Google.
