---
type: Runbook
title: Construir un cambio por capas
description: Procedimiento para llevar un cambio multi-etapa del repo de la decisión al merge mediante tickets delegados, revisión con contexto fresco y verificación sobre main.
tags: [runbook, proceso, agentes]
status: draft
owner: human:jisequilla
stale_after: 2027-04-30T00:00:00Z
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T19:20:13Z }
---

# Disparador

Un cambio que toca varias capas (estándar, scripts, skills, `knowledge/`) o más ficheros de los que una sesión puede revisar con atención. Los arreglos pequeños, la depuración con causa desconocida y los diseños sin cerrar no usan este runbook: se hacen inline o se aclaran antes con el owner. La decisión está en [ADR-0009](/decisiones/ADR-0009-construir-por-capas-y-tickets.md).

# Pasos

1. **Decidir con el owner.** Lo que es una decisión (un ADR nuevo con `okf-capture`, el vocabulario, un glosario de términos) no es un ticket: se cierra con el owner antes de construir.
2. **Partir en capas** en orden de dependencia, y cada capa en tickets de como máximo unos 50 ficheros con una lista de ficheros cerrada. Como máximo 3 tickets en paralelo.
3. **Escribir cada ticket** con:
   - comportamiento como tabla de entrada → salida esperada;
   - patrón a copiar como `fichero:línea`;
   - criterios de aceptación, cada uno con el test (o la comprobación) que falla si se revierte el cambio;
   - "se apoya en": lo que ya debe existir en main; si no existe, el builder para;
   - comandos de verificación exactos (`make test`, `make lint`, el grep de la capa).
4. **Abrir un registro por ticket** en el tracker que se use y guardar en él el texto del ticket.
5. **Ejecutar cada ticket:**
   1. *Pre-flight*: un agente lee el ticket contra el código y señala premisas falsas, ambigüedades y decisiones que son del owner.
   2. *Builder*: trabaja en un worktree, demuestra cada criterio (revertir → rojo → restaurar), pega la salida en el cuerpo del PR y abre el PR en draft.
   3. *Revisión*: uno o dos revisores con contexto fresco, sin el informe del builder. Usar dos lentes (corrección, tests) si se toca el estándar, el linter o un skill. Los hallazgos se clasifican como bloqueante, a corregir o nit; solo los bloqueantes fuerzan una ronda de arreglos.
   4. *Arreglos*: como máximo dos rondas; si no basta, el ticket vuelve al owner.
6. **Verificar y mergear desde la sesión principal:** ejecutar `make test` y `make lint` sobre main con la rama mergeada, mergear el PR y cerrar el registro citando el PR. Los nits pendientes van a un único registro de seguimiento.
7. **Subir main antes de la capa siguiente.** Los worktrees de los agentes salen de `origin/main`, no del main local: una capa mergeada solo en local es invisible para la siguiente.

# Avisos

- El informe de un agente es una afirmación: el estado se lee del PR y de la salida de las comprobaciones, no de la respuesta (que puede llegar truncada).
- Lanzar un workflow de agentes requiere un mensaje escrito del owner que nombre los tickets; una aprobación dada por un diálogo de preguntas no basta.
- Un agente solo detiene procesos que él mismo ha arrancado, nunca por nombre de proceso.
- Reanudar un workflow vuelve a ejecutar los agentes posteriores al primer cambio: para continuar una ejecución a medias, pasar su estado (PR, rama, etapa) como punto de partida.

# Rollback

Cada ticket es un PR propio: revertir el merge del PR afectado. Si una capa ya tiene tickets dependientes mergeados, revertir en orden inverso de capas.
