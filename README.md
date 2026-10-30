# j3r3-okf-builder

Estándar de conocimiento de proyecto basado en **OKF (Open Knowledge Format v0.2, Google)** y plugin de Claude Code / Cowork para aplicarlo en cualquier repositorio.

## Este repo usa OKF

El conocimiento del proyecto (decisiones, arquitectura, runbooks, políticas) está en [`knowledge/`](knowledge/index.md). Cualquier agente empieza por ahí; `AGENTS.md` (importado por `CLAUDE.md` y `GEMINI.md`) fija las reglas.

## Fuente única y proyecciones

Los skills viven una vez en `plugin/okf-builder/skills/`. Cada plataforma recibe una proyección:

| Plataforma | Proyección | Cómo |
|---|---|---|
| Claude Code | `.claude/skills` → symlink | al clonar |
| GitHub Copilot, Gemini CLI | `.agents/skills` → symlink | al clonar |
| Claude Cowork | `okf-builder.plugin` | `make plugin` |
| Microsoft 365 Copilot | `dist/m365/okf-builder-m365.zip` + `dist/m365/skills/*.zip` | `make m365` |
| Otros repos | `dist/copilot/` (`.github/skills` + `@okf` agent) | `make copilot` |

`make all` genera todo tras pasar `make test`. En Windows sin `core.symlinks`, usar `make copilot` y copiar.

## Contenido

| Ruta | Qué es |
|---|---|
| `standard/OKF-STANDARD.md` | El estándar: perfil `knowledge/2.0` (estructura, frontmatter, tipos, ciclo de vida, conformidad). |
| `standard/OKF-COMPATIBILITY.md` | Diferencias OKF v0.1 ↔ v0.2, matriz de campos, reglas de mapeo y política de versiones. |
| `templates/` | Plantillas de concepto (`{{marcadores}}`): ADR, runbook, sistema, API, tabla, métrica, término, política, vista, referencia, proyecto. |
| `knowledge/` | Conocimiento del propio proyecto (bundle OKF conformante, 8 ADR). |
| `tools/` | Exportadores de proyecciones (Copilot, M365). |
| `plugin/okf-builder/` | Plugin / fuente única: skills `okf-standard`, `okf-init`, `okf-capture`, `okf-lint`, `okf-index`, `okf-ask`, `okf-migrate` + scripts Python sin dependencias. |
| `examples/knowledge/` | Bundle de ejemplo conformante. |
| `.claude-plugin/marketplace.json` | Este repo actúa como marketplace de plugins. |

## Instalación del plugin

Desde Claude Code (repo publicado en GitHub):

```
/plugin marketplace add <owner>/j3r3-okf-builder
/plugin install okf-builder@j3r3-okf-builder
```

En local, sin publicar:

```
claude --plugin-dir ./plugin/okf-builder
```

En Cowork: cargar el fichero `.plugin` generado con `make plugin` (o el entregado en el chat).

## Uso en un proyecto

```
okf-init        → crea knowledge/ (index.md, log.md, project.md, subdirectorios)
okf-capture     → "documenta esta decisión / crea un runbook / registra este servicio"
okf-lint        → valida spec + perfil (apto para CI: python3 tools/okf/okf_lint.py knowledge --strict)
okf-index       → regenera index.md desde el frontmatter
okf-ask         → "¿por qué decidimos X?" navegando el bundle y citando confianza
okf-migrate     → detecta versión y migra 0.1 ↔ 0.2 (siempre con --dry-run primero)
```

## Scripts directamente

```bash
python3 plugin/okf-builder/skills/okf-standard/scripts/okf_init.py  --root . --title "Mi proyecto" --description "…" --actor human:<id>
python3 plugin/okf-builder/skills/okf-standard/scripts/okf_lint.py  knowledge [--json] [--strict] [--no-profile]
python3 plugin/okf-builder/skills/okf-standard/scripts/okf_index.py knowledge [--check] [--dir decisions]
python3 plugin/okf-builder/skills/okf-standard/scripts/okf_migrate.py knowledge --to 0.2 --dry-run
```

## Uso con GitHub Copilot (y otros agentes)

Los skills siguen el estándar [Agent Skills](https://agentskills.io) que Copilot descubre en `.github/skills/` (VS Code agent mode, Copilot CLI, coding agent). `make copilot` genera `dist/copilot/` con:

- `.github/skills/okf-*/` — los 7 skills con scripts y plantillas, rutas reescritas (sin `${CLAUDE_PLUGIN_ROOT}`).
- `.github/agents/okf.agent.md` — custom agent `@okf`.
- `AGENTS.okf.md` — fragmento para `AGENTS.md`.

Copia `dist/copilot/.` en la raíz del repo destino. Claude Code también lee `.github/skills/`, así que un repo con el pack funciona con ambos sin el plugin. Variante neutra: `python3 tools/export_copilot.py --skills-dir .agents/skills`.

## Uso con Microsoft 365 Copilot

M365 Copilot (Cowork, Copilot Studio, Agent Builder) acepta Agent Skills en el mismo formato `SKILL.md`. `make m365` genera:

- `dist/m365/okf-builder-m365.zip` — plugin de **M365 Copilot Cowork** (manifest v1.28 + 7 skills autocontenidos). Subida por admin (Manage apps → Upload custom app) o personal con `atk install --file-path … --scope Personal`. Cowork requiere hoy el programa Frontier.
- `dist/m365/skills/okf-*.zip` — un zip por skill para **Copilot Studio / Agent Builder** → Build → Skills → Upload a skill (GA).

El conocimiento (`knowledge/`) no es accesible desde M365 Copilot vía git: sincronízalo a SharePoint/OneDrive y añádelo como fuente de conocimiento del agente. Es markdown plano, se indexa tal cual.

## Referencias

- Spec OKF: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf (copia en `plugin/okf-builder/skills/okf-standard/references/`, Apache-2.0)
- Anuncio: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing

## Licencia

Apache-2.0 (ver [`LICENSE`](LICENSE)). Las specs OKF de Google en `references/` son copias literales bajo su propia licencia Apache-2.0 ([`OKF-SPEC-LICENSE.md`](plugin/okf-builder/skills/okf-standard/references/OKF-SPEC-LICENSE.md)).
