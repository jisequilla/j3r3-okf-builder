---
type: Decisión de Arquitectura
title: "ADR-0005: generated obligatorio y verified solo por personas"
description: El perfil exige generated en todo concepto y prohíbe que un agente escriba verified con actor human:.
tags: [adr, confianza]
status: stable
adr_id: ADR-0005
decision_status: aceptada
generated: { by: okf-builder/claude-fable-5-1, at: 2026-10-30T17:00:00Z }
---

# Contexto

OKF v0.2 deriva el nivel de confianza de `verified`: cualquier actor `human:` eleva el concepto a *human-reviewed*. Si un agente lo escribiera, la señal perdería todo su valor.

# Decisión

1. `generated: { by, at }` es obligatorio en el perfil (la spec lo deja opcional). Actor: `human:<id>` si la persona dicta el contenido, `okf-builder/<modelo>` si lo sintetiza el agente.
2. Ningún skill ni script añade `verified`. Solo tras confirmación explícita de la persona se añade `verified: { by: human:<id>, at }` y se pasa a `status: stable`.
3. Todo concepto nace en `status: draft`.

# Consecuencias

- Positivas: la confianza derivada es fiable; se distingue lo que ha mirado una persona.
- Negativas: fricción al crear (un paso humano más); es el coste buscado.
