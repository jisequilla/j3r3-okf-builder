# okf-builder's build: platform packages, root copies and checks. `just` lists the recipes.

scripts := "plugin/okf-builder/skills/okf-standard/scripts"

[private]
default:
    @just --list

# Each script's own tests, then every cross-script check; name steps to run only those (build/checks.py --list)
test *steps:
    uv run -q build/checks.py {{steps}}

# This repo's knowledge/ at --strict and the example bundle, both at 0 errors
lint:
    uv run -q {{scripts}}/okf_lint.py knowledge --strict
    uv run -q {{scripts}}/okf_lint.py examples/knowledge

# The root standard/ and templates/, copied from the okf-standard skill: edit there, then run this
copies out=".":
    python3 build/copies.py {{out}}

# Claude Cowork plugin: okf-builder.plugin
plugin:
    cd plugin/okf-builder && zip -qr ../../okf-builder.plugin . -x "*.DS_Store" -x "*__pycache__*"
    @echo "→ okf-builder.plugin"

# GitHub Copilot pack for other repos: dist/copilot and dist/okf-copilot-pack.zip
copilot:
    python3 build/export_copilot.py --zip
    @echo "→ dist/copilot (copy to the root of the target repo) · dist/okf-copilot-pack.zip"

# Microsoft 365 Copilot: the Cowork plugin and one zip per skill for Copilot Studio / Agent Builder
m365:
    python3 build/export_m365.py
    @echo "→ dist/m365/okf-builder-m365.zip (M365 Cowork plugin) · dist/m365/skills/*.zip (Copilot Studio / Agent Builder)"

# This repo's Obsidian viewer setup; pass --force to rewrite it
obsidian *args:
    uv run -q {{scripts}}/okf_obsidian.py knowledge {{args}}

# This repo's Knowledge Viewer page and data in dist/viewer/ (ADR-0042), rewritten on every run: a build output
viewer *args:
    uv run -q {{scripts}}/okf_viewer.py knowledge --out dist/viewer --force {{args}}

# The router session (DEC-0006): it plans and reviews, with its prompt file and a settings file that denies the file-editing tools inside the repository
router *args:
    claude -n okf-router-session --append-system-prompt-file build/sessions/router.md --settings build/sessions/router.settings.json {{args}}

# The worker session (DEC-0006): it builds, with its prompt file
worker *args:
    claude -n okf-worker-session --append-system-prompt-file build/sessions/worker.md {{args}}

# Both sessions in one herdr workspace labelled okf-builder, a tab each; if that workspace exists it is focused and nothing starts
sessions:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v herdr >/dev/null 2>&1; then
        echo "sessions: herdr is not on PATH; without it, run just router and just worker in a terminal each" >&2
        exit 1
    fi
    if ! listed=$(herdr workspace list 2>/dev/null); then
        echo "sessions: herdr's server is not running; start herdr, then run just sessions again" >&2
        exit 1
    fi
    id() { python3 -c 'import json, sys; print(json.load(sys.stdin)["result"][sys.argv[1]][sys.argv[2]])' "$@"; }
    existing=$(python3 -c 'import json, sys; print(next((w["workspace_id"] for w in json.load(sys.stdin)["result"]["workspaces"] if w["label"] == sys.argv[1]), ""))' okf-builder <<<"$listed")
    if [ -n "$existing" ]; then
        herdr workspace focus "$existing" >/dev/null
        echo "sessions: the herdr workspace okf-builder exists ($existing): focused, nothing started"
        exit 0
    fi
    created=$(herdr workspace create --cwd "{{justfile_directory()}}" --label okf-builder --focus)
    workspace=$(id workspace workspace_id <<<"$created")
    herdr tab rename "$(id tab tab_id <<<"$created")" router >/dev/null
    herdr pane run "$(id root_pane pane_id <<<"$created")" just router >/dev/null
    tab=$(herdr tab create --workspace "$workspace" --cwd "{{justfile_directory()}}" --label worker --no-focus)
    herdr pane run "$(id root_pane pane_id <<<"$tab")" just worker >/dev/null
    echo "sessions: herdr workspace okf-builder ($workspace) opened with the tabs router and worker"

# Root copies, every check, then every platform package
all: copies test plugin copilot m365

# Thorough secret scan of the bundles with gitleaks (okf-lint's SECRET_IN_BUNDLE is the quick check)
secrets:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v gitleaks >/dev/null 2>&1; then
        echo "secrets: gitleaks is not on PATH, scan skipped (https://github.com/gitleaks/gitleaks)"
        exit 0
    fi
    for d in knowledge examples/knowledge; do
        echo "gitleaks dir $d"
        gitleaks dir "$d" --no-banner --redact
    done

# Install the pre-commit hook in this clone: it refuses a commit whose staged root copies or Obsidian setup are stale
hooks:
    git config core.hooksPath .githooks
    @echo "pre-commit hook installed (.githooks/pre-commit)"

# The link packages .claude/skills and .agents/skills point at the source
check-links:
    #!/usr/bin/env bash
    for link in .claude/skills .agents/skills; do
        if [ "$(readlink "$link")" != "../plugin/okf-builder/skills" ]; then
            echo "broken symlink $link: ln -sfn ../plugin/okf-builder/skills $link"
            exit 1
        fi
    done
    echo "link packages .claude/skills and .agents/skills OK"
