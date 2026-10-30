---
name: okf-init
description: Crea la estructura estándar knowledge/ (bundle OKF v0.2, perfil knowledge/2.0) en el repositorio actual. Usar cuando el usuario diga "inicializa OKF", "crea la carpeta knowledge", "okf init", "scaffold de conocimiento", "prepara este repo para OKF".
---

# okf-init

> **Rutas.** `<skills>` es el directorio que contiene los skills `okf-*` (el padre de este skill): `${CLAUDE_PLUGIN_ROOT}/skills` en el plugin de Claude, `.claude/skills`, `.agents/skills`, `.github/skills` o `.gemini/skills` en un repo. Los scripts viven en `<skills>/okf-standard/scripts/` y las plantillas en `<skills>/okf-standard/templates/`.

Crea `knowledge/` con `index.md`, `log.md`, `project.md` y los subdirectorios del perfil, cada uno con su `index.md`.

## Pasos

1. Localizar la raíz del repo (donde está `.git/` o el `CLAUDE.md`). Si ya existe `knowledge/index.md`, informar y preguntar si se quiere completar la estructura (el script es idempotente: no sobreescribe sin `--force`).
2. Obtener del usuario, o inferir del repo (README, `package.json`, `pom.xml`, `pyproject.toml`, remoto git), estos datos; preguntar solo lo que no se pueda inferir:
   - `title`: nombre del proyecto.
   - `description`: una frase.
   - `repo-url`: remoto git si existe.
   - `actor`: `human:<id>` del usuario (derivar del `git config user.email` antes de la `@`; confirmar).
   - `dirs`: por defecto todos los del perfil. Si el proyecto claramente no tiene datos ni métricas (p. ej. una librería), proponer omitir `data,metrics,computations`.
3. Ejecutar:
   ```bash
   python3 "<skills>/okf-standard/scripts/okf_init.py" --root <raíz> \
     --title "<title>" --description "<description>" --actor <actor> \
     --repo-url "<url>" [--dirs a,b,c] [--okf-version 0.2|0.1]
   ```
   `--okf-version 0.1` solo si el bundle debe ser consumido por herramientas que únicamente entienden 0.1; por defecto 0.2.
4. Rellenar `knowledge/project.md`: sustituir todos los marcadores `{{...}}` con lo que se sepa del repo (propósito, alcance, enlaces). Lo que no se sepa, dejar como lista con `TODO` explícito, nunca marcadores sin sustituir.
5. Añadir (o proponer añadir) al `CLAUDE.md` del repo:
   ```
   ## Conocimiento del proyecto
   El conocimiento vive en `knowledge/` (formato OKF v0.2). Empieza por `knowledge/index.md`.
   Para añadir conocimiento usa el skill okf-capture; para validar, okf-lint.
   ```
6. Ejecutar `okf-lint` (`python3 "<skills>/okf-standard/scripts/okf_lint.py" <raíz>/knowledge`) y mostrar el resultado. Los avisos `INDEX_EMPTY` en directorios vacíos son esperables.
7. Resumir en 3–5 líneas qué se creó y sugerir la primera captura (normalmente `okf-capture` con un ADR o la vista de arquitectura de contexto).

## No hacer

- No crear conceptos de ejemplo ficticios: solo estructura y `project.md`.
- No añadir `verified` a nada.
