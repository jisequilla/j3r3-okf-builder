---
type: Decisión de Arquitectura
title: "ADR-0009: Construir los cambios multi-etapa por capas y tickets delegados"
description: Los cambios que tocan varias capas del repo se dividen en tickets verificables que construyen agentes en worktrees aislados, y la sesión principal solo juzga, verifica y mergea.
tags: [adr, proceso, agentes]
status: draft
adr_id: ADR-0009
decision_status: aceptada
generated: { by: okf-builder/claude-opus-5-5, at: 2026-10-30T19:20:13Z }
---

# Contexto

Hay cambios que cruzan todo el repo: el estándar, los scripts, los skills y el propio `knowledge/` (por ejemplo, traducir el perfil o renombrar su vocabulario). Hechos en una sola conversación, mezclan decisión e implementación, se saltan etapas de verificación y dejan el trabajo a medias cuando el contexto se compacta. Un subagente solo sabe lo que dice su brief, y su informe de "terminado" es una afirmación, no una prueba.

# Decisión

Adoptamos un patrón de construcción por capas y tickets, detallado en el runbook [Construir un cambio por capas](/runbooks/construir-por-capas.md):

1. **Capas en orden de dependencia.** Lo que decide el owner (ADR, vocabulario, glosario) va primero y se mergea y se sube a `origin/main` antes de lanzar las capas que dependen de ello.
2. **Un ticket por unidad de trabajo**, preciso por ejemplos: tabla de entrada → salida esperada, lista cerrada de ficheros, patrón a copiar como `fichero:línea` y comandos de verificación exactos. Un ticket que no se puede escribir así no está listo para delegar.
3. **La sesión principal juzga y no implementa.** Cada ticket pasa por pre-flight, builder en worktree con PR en draft, uno o dos revisores con contexto fresco (sin el informe del builder) y como máximo dos rondas de arreglos.
4. **Verificación en capas, ninguna fiable por sí sola:** el builder demuestra cada criterio de aceptación (revertir → rojo → restaurar), los revisores intentan romper el diff, y la sesión principal vuelve a ejecutar `make test` y `make lint` sobre main mergeado antes de cerrar.
5. **La prosa también se verifica de forma mecánica.** Como no tiene tests, cada ticket de prosa lleva una comprobación (por ejemplo, un grep de vocabulario residual que falla con un fichero plantado) y una pasada de revisión de deriva de significado contra el glosario.
6. **Seguimiento independiente del tracker.** Cada ticket tiene su registro de trabajo (en el entorno del owner, un bead de `bd` local), que se cierra solo después del merge y con el PR citado. El repo no depende de ningún tracker.

# Alternativas consideradas

| Alternativa | Pros | Contras | Motivo de descarte |
|---|---|---|---|
| Todo en la sesión principal | Sin coste de coordinación | Mezcla juicio e implementación; las etapas se saltan; frágil ante la compactación | No escala a cambios de ~150 ficheros |
| Fan-out libre de subagentes sin tickets | Rápido | Deriva de terminología; sin criterios de aceptación; los informes se aceptan como prueba | La verificación queda en manos del implementador |
| Copiar el tooling completo de otro repo (generadores de oleadas, mutation runs, delegation log) | Probado en otro contexto | Peso desproporcionado para unos pocos tickets | KISS: se incorporará si el volumen de tickets lo justifica |

# Consecuencias

- Positivas: cada etapa deja un PR revisable; los cambios grandes resisten la compactación; cualquier agente, de cualquier plataforma, puede seguir el mismo procedimiento leyendo el runbook.
- Negativas / deuda asumida: más ceremonia por cambio; solo compensa en cambios multi-etapa, así que los arreglos pequeños se siguen haciendo inline.
- Acciones derivadas: aplicar el patrón a la migración del repo al inglés.

# Relacionados

* [Construir un cambio por capas](/runbooks/construir-por-capas.md)
* [Reglas para agentes que trabajan en este repo](/politicas/agentes-en-este-repo.md)
* [ADR-0008: dogfooding](/decisiones/ADR-0008-dogfooding.md)
