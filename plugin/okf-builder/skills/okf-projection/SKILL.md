---
name: okf-projection
description: Creates, checks, refreshes and renders the knowledge projections of an OKF bundle (projections/<slug>/, ADR-0022), derivations of the base for a reader that are not OKF. Checks each projection.yaml, the dependency rule and drift by nature with okf_projection.py, proposes the refresh of a composed or recomputable projection and applies it only after the person approves, runs a rendered projection's render only when the person asks, and never touches a frozen projection. Use when the user says "create a projection", "refresh the projections", "render this projection", "which projections are stale", "check the projections", "okf projection", or after okf-distill has listed projections to refresh.
---

# okf-projection

> **Paths.** `<skills>` is the directory that holds the `okf-*` skills (the parent of this skill): `${CLAUDE_PLUGIN_ROOT}/skills` in the Claude plugin; `.claude/skills`, `.agents/skills`, `.github/skills` or `.gemini/skills` in a repo. The scripts live in `<skills>/okf-standard/scripts/` and the templates in `<skills>/okf-standard/templates/`. Without uv, `python3` works if PyYAML is installed.

Owns `projections/`, the derivation layer (ADR-0022, ADR-0031, standard §2.1). A projection is not OKF: it is never a concept, never a source for an answer, and nothing in it is written into `base/` or `fragments/`. This skill decides nothing about content by itself: every created or refreshed content is approved by the person before it is written, and a projection's `render` command runs only when the person asks for it.

## The script

```bash
uv run "<skills>/okf-standard/scripts/okf_projection.py" <bundle> --json                      # check; executes nothing
uv run "<skills>/okf-standard/scripts/okf_projection.py" <bundle> --json --run-render         # also run each render into a temporary directory and compare (only when the person asks)
uv run "<skills>/okf-standard/scripts/okf_projection.py" <bundle> --record-hashes <slug>      # write a composed projection's current ref hashes (after the person approves its content)
```

`--json` gives `projections` (`slug`, `lifecycle`, `nature`, `frozen`), `findings` (`code`, `level`, `slug`, `message`), `not_checked` (rendered, render not run), `to_recompute` (recomputable, for a person), `frozen` and `notices`. `PROJ_DRIFT` is a warning: it asks for a refresh. Every other code is an error to fix in `projection.yaml` before anything else. `--run-render` only checks: it renders into an empty temporary directory and compares, and writes nothing in the projection.

## Steps

1. **Find the bundle** (`knowledge/index.md`, searching upwards from the cwd; if there is none, propose `okf-init` and stop) and **its OKF profile** (`okf_profile` in the root `index.md`; if missing, knowledge/2.0). Projections belong to knowledge/3.0: in a knowledge/2.0 bundle offer the migration with the `okf-migrate` skill, applied only after the person confirms, and stop.
2. **Check** with `okf_projection.py <bundle> --json`, without `--run-render`. Report the errors by slug, the `PROJ_DRIFT` warnings, `not_checked`, `to_recompute` and `frozen`. For "which projections are stale", this report is the answer: name each drifted projection with the ref or file that drifted, say that the rendered ones in `not_checked` were not checked because no render ran (and that the person can ask for it), and list `to_recompute` for a person. Then follow the step the person asks for.
3. **Create a projection.**
   - Ask the person for each key of `projection.yaml` they have not given (ADR-0022 decision 2), never inventing one: `lifecycle` (`canonical`, `deliverable` or `transient`), `nature` (`rendered`, `composed` or `recomputable`), `intent` (audience, scope, tone and what to leave out) and `refs` (the base concepts and projections it derives from, as bundle paths `/base/...` or `/projections/<slug>[/<file>]`; required for rendered and composed). A rendered projection also needs its `render` command, and a deliverable one its first `versions` entry (`version`, `date`, `commit`, and to whom it was sent) once it is delivered. Check the dependency rule before writing: a `canonical` projection references only the base and `canonical` projections; a `deliverable` one, the base, `canonical` and `deliverable`; a `transient` one, anything.
   - The slug is kebab-case and unique in `projections/`. Write `projections/<slug>/projection.yaml` and `projections/<slug>/content.md` (for a recomputable projection, the procedure over its external source). Add `render/<renderer>.md`, one input per renderer, only for a rendered projection, and `deliverables/` only when it renders files to deliver. Write nothing else.
   - **Composed**: read every ref, draft `content.md` from them following `intent`, and show it to the person. Write it only after they approve it. Write each ref as a one-line flow map with the placeholder `pending`, `- { path: /base/..., sha256: pending }`, then run `--record-hashes <slug>`, which replaces each placeholder with the ref's current `sha256`. Never type a hash by hand.
   - **Rendered**: the person gives the `render` command, which writes its files into `$OKF_PROJECTION_OUT`. Render it for real (step 4, rendered) only when the person asks.
   - **Recomputable**: `content.md` holds the procedure; the dated values go where the procedure says. Run it (step 4, recomputable) only when the person asks.
   - Then run `okf_projection.py <bundle> --json` again: it must report 0 errors for the slug.
4. **Refresh.** A projection listed under `frozen` is never refreshed, rendered or given new hashes: it keeps its last state; say so and leave it. For the rest, by nature:
   - **Composed**, for each `PROJ_DRIFT`: read the ref the finding names and what changed in it (`git diff` of that file when the bundle is in Git), propose the change to `content.md` that keeps to `intent`, and wait for the person to approve, change or reject it. Apply only what they approve. `--record-hashes <slug>` writes the current hash of every ref of the projection, so run it only once the person has settled every drifted ref of it: each change approved and applied, or the person stated that the ref's change needs no content change. While any drifted ref is rejected or left open, do not record: the content and the hashes stay as they are, and say that its drift stays reported.
   - **Rendered**: pass `--run-render` only when the person asks for the render or for a render check, never by yourself. A `PROJ_DRIFT` names the rendered file that differs or is missing; a `PROJ_RENDER_FAILED` is an error to report, never to work around. When the person asks to render for real, run the projection's `render` yourself from the bundle root with `OKF_PROJECTION_OUT` set to the projection's directory as an absolute path (`(cd <bundle> && OKF_PROJECTION_OUT="$PWD/projections/<slug>" sh -c '<render>')`, which holds for a relative or an absolute `<bundle>`), show the files it changed (`git status` and `git diff` of the projection's directory), and leave them for the person to keep or discard. Nothing is recorded for a rendered projection.
   - **Recomputable** (listed under `to_recompute`): rerun the procedure in `content.md` against its external source, show the difference between the dated values it gives and the ones the projection holds, and wait for the person's approval before writing them. A procedure this environment cannot run is reported as such, with what the person must run by hand.
5. **Deliver.** For a deliverable projection the person delivers, add the `versions` entry they give (`version`, `date`, `commit` from `git rev-parse --short HEAD`, and to whom it was sent) and keep only the latest version in `deliverables/`. A transient projection is never committed: remind the person when one is about to be.
6. **Validate** after any change with `okf_projection.py <bundle> --json`: 0 errors before finishing. `okf-lint` and `okf-index` skip `projections/`, so they need not run for a change that touched only `projections/`.
7. **Close**: what was created, refreshed or rendered and with whose approval, the drift still open, the rendered projections not checked, the recomputable ones still to recompute and the frozen ones left as they are.

## Limits

- Never write a concept, an `index.md` or a `log.md` in `projections/`, and never answer a question about the project from a projection: answers come from `base/` (`okf-ask`).
- Never pass `--run-render`, and never run a projection's `render`, unless the person asks. Checking a bundle never executes anything by itself.
- Never apply a refresh, a recomputed value or a new content without the person's approval, and never run `--record-hashes` before the person has settled every drifted ref of the projection: while one is rejected or left open, its drift stays reported.
- Never refresh, render or record hashes for a frozen projection.
