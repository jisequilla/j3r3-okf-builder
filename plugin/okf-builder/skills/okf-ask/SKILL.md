---
name: okf-ask
description: Responde preguntas sobre el proyecto consultando knowledge/ (bundle OKF) con divulgación progresiva y citando conceptos, estado y nivel de confianza. Usar cuando el usuario pregunte "¿por qué decidimos X?", "¿cómo se opera Y?", "¿qué significa Z en este proyecto?", "¿qué sabemos de…?", "consulta el conocimiento", "okf ask", o cuando una tarea de código requiera contexto de arquitectura/dominio del repo.
---

# okf-ask

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

## Pasos

1. Leer `knowledge/index.md`. Elegir los directorios relevantes por la pregunta (decisiones para "por qué", runbooks para "cómo operar", dominio para "qué significa", sistemas/arquitectura para "cómo está montado", datos/metricas para "de dónde sale este número").
2. Leer el `index.md` de esos directorios; seleccionar conceptos por `description`. Abrir solo los necesarios (máximo ~8 en una primera pasada). Seguir enlaces solo si la respuesta lo requiere. Si hace falta búsqueda textual: `grep -ril "<término>" knowledge/`.
3. Evaluar cada concepto usado:
   - `status` (`deprecated` ⇒ mencionarlo y buscar `superseded_by`).
   - `stale_after` vencido ⇒ avisar de posible obsolescencia.
   - Confianza: sin `verified` ⇒ *sin verificar*; `verified` con `human:` ⇒ *revisado por persona*; solo procesos/agentes ⇒ *confirmado por máquina*.
   - `generated.at` para la antigüedad; en bundles 0.1, `timestamp`. Fuentes: `sources[]` o, en 0.1, la sección `# Citations`.
4. Responder de forma directa y breve. Al final, bloque **Fuentes** con la ruta de cada concepto (`knowledge/decisiones/ADR-0007-....md`) y su estado/confianza en una línea. Si dos conceptos se contradicen, decirlo y preferir el más reciente verificado.
5. Si el conocimiento no está en el bundle: decirlo explícitamente, responder con lo que se pueda deducir del código marcándolo como *no documentado*, y ofrecer `okf-capture` para registrarlo. Si al responder se detecta un error en un concepto, proponer la corrección (no aplicarla sin confirmación).

## No hacer

- No responder desde memoria general del framework/tecnología cuando el bundle contiene una decisión específica del proyecto: la decisión del proyecto manda.
- No presentar conceptos `draft` o sin verificar como hechos establecidos sin señalarlo.
