---
name: okf-capture
description: Captura una unidad de conocimiento en knowledge/ usando la plantilla OKF adecuada (ADR, runbook, sistema, API, tabla, métrica, término, política, vista de arquitectura, referencia). Usar cuando el usuario diga "documenta esta decisión", "crea un ADR", "añade un runbook", "registra este sistema", "captura esto en knowledge", "okf capture", o cuando tras resolver una tarea se haya producido conocimiento que debería persistir.
---

# okf-capture

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

Convierte conocimiento (decisión, procedimiento, componente, definición) en un concepto OKF correctamente tipado, enlazado y registrado.

## Pasos

1. **Localizar el bundle** (`knowledge/index.md` hacia arriba desde el cwd; si no existe, proponer `okf-init` y parar) y **su versión** (`okf_version` del `index.md` raíz; si falta, `okf_lint.py --json` → `okf_version`). Se escribe en esa versión.
2. **Clasificar**: elegir `type` y directorio según la tabla de `okf-standard`. Si el usuario no lo dice, inferirlo del contenido y confirmarlo en una línea. Casos frecuentes:
   - "decidimos usar X en vez de Y" → Decisión de Arquitectura (`decisiones/ADR-NNNN-slug.md`, NNNN = máximo existente + 1, 4 dígitos).
   - "cuando salta la alerta X hacemos…" → Runbook.
   - "el servicio X hace…, expone…, depende de…" → Sistema (+ API si hay contrato).
   - "X significa…" → Término.
   - "la métrica X se calcula…" → Métrica + Attested Computation si hay SQL/código sancionado.
3. **Leer contexto existente** antes de escribir: el `index.md` del directorio destino y los conceptos que se vayan a enlazar (sistemas, ADRs previos). Detectar duplicados: si ya existe un concepto equivalente, proponer actualizarlo (y, si cambia la decisión, deprecarlo y crear el nuevo con `supersedes`/`superseded_by`).
4. **Redactar** a partir de la plantilla `<skills>/okf-standard/templates/<tipo>.md`:
   - Sustituir todos los `{{...}}`. `actor` = quien aporta el contenido: si lo dicta el usuario y Claude solo lo formatea, `human:<id>`; si Claude lo sintetiza del código/repo, `okf-builder/<modelo>`. `ahora` = UTC ISO 8601 `YYYY-MM-DDTHH:MM:SSZ`.
   - `status: draft` siempre al crear. **No** añadir `verified`.
   - `description`: una frase autónoma.
   - Enlaces absolutos al bundle (`/sistemas/x.md`). Enlazar aunque el destino no exista aún; listar al final los enlaces pendientes.
   - Si el contenido deriva de fuentes (docs, tickets, URLs, ficheros del repo): `sources[]` con `resource` e `id`, y notas al pie `[^id]` en las afirmaciones que lo necesiten. Para ficheros del repo usar rutas relativas al repo como `resource`.
   - Secciones vacías de la plantilla: eliminarlas o dejar un `TODO` explícito, nunca marcadores.
   - **Bundle 0.1**: tras guardar, ejecutar `python3 "<skills>/okf-standard/scripts/okf_migrate.py" <bundle> --to 0.1 --file <ruta-relativa>` para convertir `generated`→`timestamp` y `sources`→`# Citations`; no dejar claves 0.2 en un bundle 0.1.
5. **Registrar**: añadir entrada en `knowledge/log.md` bajo la fecha de hoy (crear la sección si no existe, encima de las anteriores): `* **Creación**: ...` / `* **Actualización**: ...` / `* **Deprecación**: ...`, con enlace al concepto. Si el directorio tiene su propio `log.md`, también.
6. **Indexar y validar**:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir <directorio>
   python3 "<skills>/okf-standard/scripts/okf_index.py" <bundle> --dir .
   python3 "<skills>/okf-standard/scripts/okf_lint.py" <bundle>
   ```
   Corregir cualquier ERROR antes de terminar.
7. **Cerrar**: mostrar ruta del concepto, `type`, enlaces pendientes y recordar que queda en `draft` hasta que una persona añada `verified: { by: human:<id>, at: ... }` y pase a `stable` (ofrecer hacerlo si el usuario confirma que lo ha revisado: entonces sí usar `human:<id>` del usuario).

## Captura por lotes

Si el usuario pide "documenta los servicios de este repo" o similar: inventariar primero (lista de candidatos con type y ruta propuesta), confirmar, y luego crear uno a uno siguiendo los pasos 4–6. Máximo 15 conceptos por lote sin nueva confirmación.
