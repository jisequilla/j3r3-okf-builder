---
name: okf-index
description: Regenera los index.md de knowledge/ a partir del frontmatter de los conceptos (agrupados por type, con description) y comprueba si están desactualizados. Usar cuando el usuario diga "regenera los índices", "okf index", "actualiza index.md", o después de añadir/mover/deprecar conceptos.
---

# okf-index

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

## Pasos

1. Comprobar estado sin escribir:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] --check
   ```
2. Regenerar (todos o un directorio):
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_index.py" [<bundle>] [--dir <subdir>]
   ```
3. Reglas que aplica el generador (no duplicarlas a mano):
   - Secciones por `type` en el orden del perfil; entradas `* [title](fichero.md) - description`, con sufijo `_(draft)_` / `_(deprecated)_`.
   - Sección `# Subdirectories` con la descripción del blockquote `> ...` del `index.md` hijo o la del perfil.
   - Raíz: conserva el frontmatter (`okf_version`, `okf_profile`) y cualquier sección `# Notas...` escrita a mano. En subdirectorios conserva también `# Notas...`.
4. Mostrar el diff resumido (qué índices cambiaron) y registrar en `log.md` solo si el cambio es relevante (p. ej. reorganización), no por cada regeneración rutinaria.
