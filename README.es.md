[Read in English](README.md)

# j3r3-okf-builder

Estándar de conocimiento de proyecto basado en **OKF (Open Knowledge Format v0.2, Google)** y plugin que lo aplica en cualquier repositorio. El conocimiento del proyecto (decisiones, arquitectura, runbooks, políticas) vive en `knowledge/` como un bundle OKF con el perfil `knowledge/2.0`. Los skills crean la estructura, capturan conceptos con plantillas, validan, regeneran índices, responden preguntas y migran entre versiones.

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

`make all` genera todo tras pasar `make test`. En Windows sin `core.symlinks`, usa `make copilot` y copia.

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

## Idioma

Los skills, las plantillas y el conocimiento están en inglés, pero los agentes responden en el idioma de quien les escribe: si les hablas en español, contestan en español.

## Licencia

Apache-2.0 (ver [`LICENSE`](LICENSE)).
