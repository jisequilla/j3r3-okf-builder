---
type: Architecture Decision
title: "ADR-0008: El repo okf-builder documenta su propio conocimiento con OKF"
description: Este repositorio aplica el perfil knowledge/1.0 a sí mismo; las decisiones del proyecto son ADRs en knowledge/decisions.
tags: [adr, proceso]
status: stable
adr_id: ADR-0008
decision_status: accepted
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

Las decisiones de diseño del estándar y del plugin vivían en conversaciones con el agente. Un estándar de conocimiento que no se usa a sí mismo no es creíble ni se prueba de verdad.

# Decisión

`knowledge/` en la raíz de este repo, conformante con el perfil, validado en `make lint` con `--strict`. Cualquier agente que trabaje en el repo lee primero `knowledge/index.md` (regla en [AGENTS.md](/policies/agents-in-this-repo.md)). Los cambios de decisión se registran como nuevos ADR que sustituyen al anterior.

# Consecuencias

- Positivas: el estándar se prueba en uso real; los agentes de cualquier plataforma heredan el contexto; la historia de decisiones es consultable.
- Negativas: disciplina de mantenimiento; mitigada porque `okf-capture` y `okf-lint` hacen el trabajo mecánico.
