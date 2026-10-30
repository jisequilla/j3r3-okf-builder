# AGENTS.md — okf-builder

This repository defines the **OKF standard (knowledge/2.0 profile)** and the `okf-builder` plugin that applies it. The repo uses OKF itself: its knowledge lives in `knowledge/` (start at `knowledge/index.md`).

## Single source and projections

- Source of truth for the skills: `plugin/okf-builder/skills/` (Agent Skills standard, `SKILL.md`). Scripts in `okf-standard/scripts/`, templates in `okf-standard/templates/`.
- Symlinked projections: `.claude/skills` (Claude Code) and `.agents/skills` (GitHub Copilot, Gemini CLI) → the source. Do not edit there.
- Generated projections: `make plugin` (Claude Cowork, `.plugin`), `make m365` (Microsoft 365 Copilot), `make copilot` (vendorable pack for other repos). Output in `dist/` (ignored by git).
- Context files: this `AGENTS.md` is the shared one; `CLAUDE.md` and `GEMINI.md` import it.

## Rules for any agent

1. Before changing the standard, the skills or the scripts: read `knowledge/decisions/` (ADRs). If the decision changes, write a new ADR that supersedes the previous one (`okf-capture`); never edit history.
2. Every change in `knowledge/` ends with `python3 plugin/okf-builder/skills/okf-standard/scripts/okf_lint.py knowledge --strict` at 0 errors (`make lint`).
3. Every change in skills/scripts ends with `make test` (init 0.1/0.2, Google fixtures v0.1/v0.2, round-trip migration).
4. Do not add `verified: human:` to any concept unless a person explicitly confirms it.
5. Skills must not depend on vendor variables (`${CLAUDE_PLUGIN_ROOT}` appears only in the paths note); use the `<skills>/...` convention.
6. Google's specs in `references/` are verbatim copies (Apache-2.0): they are not edited; they are updated from upstream and the update is recorded in `log.md`.

## Quick map

| Path | What it is |
|---|---|
| `knowledge/` | Project knowledge (OKF bundle) |
| `standard/` | Standard and compatibility matrix (canonical copies also in `okf-standard/references/`) |
| `plugin/okf-builder/` | Plugin / skills source |
| `tools/` | Exporters (Copilot, M365) |
| `examples/` | Example bundle and Google fixtures |
