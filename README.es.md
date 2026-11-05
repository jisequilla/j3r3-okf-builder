[Read in English](README.md)

# j3r3-okf-builder

Estándar de conocimiento de proyecto basado en **OKF (Open Knowledge Format v0.2, Google)** y plugin que lo aplica en cualquier repositorio. El conocimiento del proyecto (decisiones, arquitectura, runbooks, políticas) vive en `knowledge/` como un bundle OKF con el perfil `knowledge/3.0`. Los skills crean la estructura, capturan conceptos con plantillas, validan, regeneran índices, responden preguntas y migran entre versiones.

El repo está en inglés. Este resumen sirve a quien habla español; el detalle completo está en [README.md](README.md).

## Instalación por plataforma

Los skills viven una vez en `plugin/okf-builder/skills/`; cada plataforma recibe una proyección.

- **Claude Code**: `.claude/skills` es un enlace simbólico a la fuente y funciona al clonar. Desde un repo publicado en GitHub:

  ```
  /plugin marketplace add <owner>/j3r3-okf-builder
  /plugin install okf-builder@j3r3-okf-builder
  ```

  En local, sin publicar: `claude --plugin-dir ./plugin/okf-builder`.
- **GitHub Copilot**: `.agents/skills` funciona al clonar. Para otros repos, `make copilot` genera `dist/copilot/` (`.github/skills` + agente `@okf`); copia `dist/copilot/.` en la raíz del repo destino.
- **Gemini CLI**: igual que Copilot, mediante `.agents/skills` al clonar.
- **Claude Cowork**: `make plugin` genera `okf-builder.plugin`; cárgalo en Cowork.
- **Microsoft 365 Copilot**: `make m365` genera `dist/m365/okf-builder-m365.zip` (plugin de Cowork) y `dist/m365/skills/*.zip` (un zip por skill para Copilot Studio / Agent Builder).

`make all` regenera las copias de la raíz y genera todo tras pasar `make test`. En Windows sin `core.symlinks`, usa `make copilot` y copia.

## Contenido

Cada fichero pertenece a uno de cuatro hogares ([ADR-0028](knowledge/base/decisions/ADR-0028-where-things-go.md)):

- **Producto**: `plugin/okf-builder/` (la única fuente: skills, scripts, plantillas, el estándar y el agente `knowledge-architect`), `standard/`, `templates/` y `.claude-plugin/marketplace.json`.
- **Construcción del producto**: `Makefile`, `build/` (exportadores de Copilot y M365, y la configuración del agente de M365), `tests/` y `examples/`.
- **Conocimiento**: `knowledge/`, el bundle OKF del propio proyecto.
- **Espacio de trabajo**: `.claude/`, `.agents/`, `.beads/` y los ficheros de contexto (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`).

El plugin es la única fuente del estándar y las plantillas: `standard/` y `templates/` en la raíz son copias generadas por `make copies`, y `make test` falla si están desfasadas. Para cambiarlas, edita `plugin/okf-builder/skills/okf-standard/` y ejecuta `make copies`.

## Uso

```
okf-init        → crea knowledge/
okf-capture     → "documenta esta decisión / crea un runbook"
okf-fragment    → "guarda esta reunión / esta transcripción" como fragmento, tal como ocurrió
okf-distill     → propone qué cambia un fragmento en el bundle; aplica solo lo que apruebas
okf-review      → doble check: cambios desde la última revisión, conflictos abiertos, borradores sin verificar
okf-lint        → valida spec + perfil
okf-index       → regenera index.md desde el frontmatter
okf-ask         → "¿por qué decidimos X?"
okf-migrate     → migra 0.1 ↔ 0.2 (siempre con --dry-run primero)
```

`okf-lint` informa de una credencial guardada en un fichero del bundle como `SECRET_IN_BUNDLE`, una comprobación rápida. Para pre-commit y CI usa [gitleaks](https://github.com/gitleaks/gitleaks), el escáner a fondo: `make secrets` ejecuta `gitleaks dir` sobre los bundles de este repo.

## Idioma

Los skills, las plantillas y el conocimiento están en inglés, pero los agentes responden en el idioma de quien les escribe: si les hablas en español, contestan en español.

## Licencia

Apache-2.0 (ver [`LICENSE`](LICENSE)).
