[Leer en español](README.es.md)

# j3r3-okf-builder

A project knowledge standard based on **OKF (Open Knowledge Format v0.2, Google)**, and a Claude Code / Cowork plugin that applies it in any repository.

## This repo uses OKF

The project's knowledge (decisions, architecture, runbooks, policies) lives in [`knowledge/`](knowledge/index.md). Every agent starts there; `AGENTS.md` (imported by `CLAUDE.md` and `GEMINI.md`) sets the rules.

## Single source and projections

The skills live once, in `plugin/okf-builder/skills/`. Each platform gets a projection:

| Platform | Projection | How |
|---|---|---|
| Claude Code | `.claude/skills` → symlink | on clone |
| GitHub Copilot, Gemini CLI | `.agents/skills` → symlink | on clone |
| Claude Cowork | `okf-builder.plugin` | `make plugin` |
| Microsoft 365 Copilot | `dist/m365/okf-builder-m365.zip` + `dist/m365/skills/*.zip` | `make m365` |
| Other repos | `dist/copilot/` (`.github/skills` + `@okf` agent) | `make copilot` |

`make all` builds everything once `make test` passes. On Windows without `core.symlinks`, use `make copilot` and copy.

## Contents

| Path | What it is |
|---|---|
| `standard/OKF-STANDARD.md` | The standard: the `knowledge/2.0` profile (structure, frontmatter, types, lifecycle, conformance). |
| `standard/OKF-COMPATIBILITY.md` | OKF v0.1 ↔ v0.2 differences, field matrix, mapping rules and versioning policy. |
| `templates/` | Concept templates (`{{placeholders}}`): ADR, runbook, system, API, table, metric, term, policy, view, reference, project. |
| `knowledge/` | The project's own knowledge (a conformant OKF bundle, 8 ADRs). |
| `tools/` | Projection exporters (Copilot, M365). |
| `plugin/okf-builder/` | Plugin / single source: the skills `okf-standard`, `okf-init`, `okf-capture`, `okf-lint`, `okf-index`, `okf-ask`, `okf-migrate` + Python scripts run with uv (PEP 723). |
| `examples/knowledge/` | A conformant example bundle. |
| `.claude-plugin/marketplace.json` | This repo acts as a plugin marketplace. |

## Installing the plugin

From Claude Code (repo published on GitHub):

```
/plugin marketplace add <owner>/j3r3-okf-builder
/plugin install okf-builder@j3r3-okf-builder
```

Locally, without publishing:

```
claude --plugin-dir ./plugin/okf-builder
```

In Cowork: load the `.plugin` file built by `make plugin` (or the one delivered in the chat).

## Using it in a project

```
okf-init        → creates knowledge/ (index.md, log.md, project.md, subdirectories)
okf-capture     → "document this decision / create a runbook / register this service"
okf-lint        → validates spec + profile (CI-ready: uv run tools/okf/okf_lint.py knowledge --strict)
okf-index       → regenerates index.md from the frontmatter
okf-ask         → "why did we decide X?" by navigating the bundle and citing trust level
okf-migrate     → detects the version and migrates 0.1 ↔ 0.2 (always --dry-run first)
```

## Running the scripts directly

```bash
uv run plugin/okf-builder/skills/okf-standard/scripts/okf_init.py  --root . --title "My project" --description "…" --actor human:<id>
uv run plugin/okf-builder/skills/okf-standard/scripts/okf_lint.py  knowledge [--json] [--strict] [--no-profile]
uv run plugin/okf-builder/skills/okf-standard/scripts/okf_index.py knowledge [--check] [--dir decisions]
uv run plugin/okf-builder/skills/okf-standard/scripts/okf_migrate.py knowledge --to 0.2 --dry-run
```

## Using it with GitHub Copilot (and other agents)

The skills follow the [Agent Skills](https://agentskills.io) standard, which Copilot discovers in `.github/skills/` (VS Code agent mode, Copilot CLI, coding agent). `make copilot` builds `dist/copilot/` with:

- `.github/skills/okf-*/` — the 7 skills with scripts and templates, paths rewritten (no `${CLAUDE_PLUGIN_ROOT}`).
- `.github/agents/okf.agent.md` — the `@okf` custom agent.
- `AGENTS.okf.md` — a fragment for `AGENTS.md`.

Copy `dist/copilot/.` into the root of the target repo. Claude Code also reads `.github/skills/`, so a repo with the pack works with both, without the plugin. Neutral variant: `python3 tools/export_copilot.py --skills-dir .agents/skills`.

## Using it with Microsoft 365 Copilot

M365 Copilot (Cowork, Copilot Studio, Agent Builder) accepts Agent Skills in the same `SKILL.md` format. `make m365` builds:

- `dist/m365/okf-builder-m365.zip` — an **M365 Copilot Cowork** plugin (manifest v1.28 + 7 self-contained skills). Uploaded by an admin (Manage apps → Upload custom app) or personally with `atk install --file-path … --scope Personal`. Cowork currently requires the Frontier program.
- `dist/m365/skills/okf-*.zip` — one zip per skill for **Copilot Studio / Agent Builder** → Build → Skills → Upload a skill (GA).

M365 Copilot cannot reach the knowledge (`knowledge/`) through git: sync it to SharePoint/OneDrive and add it as a knowledge source for the agent. It is plain markdown and is indexed as is.

## References

- OKF spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf (copy in `plugin/okf-builder/skills/okf-standard/references/`, Apache-2.0)
- Announcement: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing

## License

Apache-2.0 (see [`LICENSE`](LICENSE)). Google's OKF specs in `references/` are verbatim copies under their own Apache-2.0 license ([`OKF-SPEC-LICENSE.md`](plugin/okf-builder/skills/okf-standard/references/OKF-SPEC-LICENSE.md)).
