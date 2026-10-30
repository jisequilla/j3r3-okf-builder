# AGENTS.md — okf-builder

Este repositorio define el **estándar OKF (perfil knowledge/2.0)** y el plugin `okf-builder` que lo aplica. El propio repo usa OKF: su conocimiento está en `knowledge/` (empieza por `knowledge/index.md`).

## Fuente única y proyecciones

- Fuente de verdad de los skills: `plugin/okf-builder/skills/` (estándar Agent Skills, `SKILL.md`). Scripts en `okf-standard/scripts/`, plantillas en `okf-standard/templates/`.
- Proyecciones por enlace simbólico: `.claude/skills` (Claude Code) y `.agents/skills` (GitHub Copilot, Gemini CLI) → la fuente. No editar ahí.
- Proyecciones generadas: `make plugin` (Claude Cowork, `.plugin`), `make m365` (Microsoft 365 Copilot), `make copilot` (pack vendorizable para otros repos). Salida en `dist/` (ignorado por git).
- Ficheros de contexto: este `AGENTS.md` es el común; `CLAUDE.md` y `GEMINI.md` lo importan.

## Reglas para cualquier agente

1. Antes de cambiar el estándar, los skills o los scripts: leer `knowledge/decisions/` (ADRs). Si la decisión cambia, nuevo ADR que sustituye al anterior (`okf-capture`), nunca editar la historia.
2. Todo cambio en `knowledge/` termina con `python3 plugin/okf-builder/skills/okf-standard/scripts/okf_lint.py knowledge --strict` a 0 errores (`make lint`).
3. Todo cambio en skills/scripts termina con `make test` (init 0.1/0.2, fixtures de Google v0.1/v0.2, migración round-trip).
4. No añadir `verified: human:` a ningún concepto sin que una persona lo confirme explícitamente.
5. Los skills no deben depender de variables de un vendor (`${CLAUDE_PLUGIN_ROOT}` solo aparece en la nota de rutas); usar la convención `<skills>/...`.
6. Las specs de Google en `references/` son copias literales (Apache-2.0): no se editan; se actualizan desde el upstream y se registra en `log.md`.

## Mapa rápido

| Ruta | Qué es |
|---|---|
| `knowledge/` | Conocimiento del proyecto (bundle OKF) |
| `standard/` | Estándar y matriz de compatibilidad (copias canónicas también en `okf-standard/references/`) |
| `plugin/okf-builder/` | Plugin / fuente de skills |
| `tools/` | Exportadores (Copilot, M365) |
| `examples/` | Bundle de ejemplo y fixtures de Google |
