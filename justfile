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

# The router session (DEC-0006): it plans and reviews, with its prompt file and a settings file that denies the file-editing tools inside the repository; a --model or --effort in the arguments replaces the recipe's
router *args:
    claude -n okf-router-session --append-system-prompt-file build/sessions/router.md --settings build/sessions/router.settings.json --model claude-fable-5-2 --effort low {{args}}

# The worker session (DEC-0006): it builds, with its prompt file; a --model or --effort in the arguments replaces the recipe's
worker *args:
    claude -n okf-worker-session --append-system-prompt-file build/sessions/worker.md --model claude-opus-5-5 --effort medium {{args}}

# Both sessions, each in an hc terminal named after it that outlives this one, started with this shell's PATH and just's own path because hc looks programs up on its server's PATH; a session already live under its name is reported and not started again; with herdr-app on PATH and Herdr.app open, each is shown in its space okf-builder, created if missing, in a tab named router or worker, and the last line names only the sessions placed there
sessions:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v hc >/dev/null 2>&1; then
        echo "sessions: hc is not on PATH; without it, run just router and just worker in a terminal each" >&2
        exit 1
    fi
    if ! hc server status >/dev/null 2>&1; then
        echo "sessions: hc's server is not running; start it with hc server start, then run just sessions again" >&2
        exit 1
    fi
    if ! command -v claude >/dev/null 2>&1; then
        echo "sessions: claude is not on PATH, and the sessions hc starts get this PATH" >&2
        exit 1
    fi
    live() { hc get --json "$1" 2>/dev/null | grep -Eq '"state": *"live"'; }
    if live okf-router-session; then
        echo "sessions: okf-router-session is already running"
    else
        hc run --bg --no-parent --name okf-router-session --cwd "{{justfile_directory()}}" /usr/bin/env PATH="$PATH" "{{just_executable()}}" router >/dev/null
        echo "sessions: okf-router-session started"
    fi
    if live okf-worker-session; then
        echo "sessions: okf-worker-session is already running"
    else
        hc run --bg --no-parent --name okf-worker-session --cwd "{{justfile_directory()}}" /usr/bin/env PATH="$PATH" "{{just_executable()}}" worker >/dev/null
        echo "sessions: okf-worker-session started"
    fi
    if ! live okf-router-session || ! live okf-worker-session; then
        echo "sessions: hc does not show both okf-router-session and okf-worker-session as live" >&2
        exit 1
    fi
    if ! command -v herdr-app >/dev/null 2>&1; then
        echo "sessions: herdr-app is not on PATH, so the sessions were not placed in the Herdr.app space okf-builder; reach them with hc attach okf-router-session and hc attach okf-worker-session"
        exit 0
    fi
    if ! listed=$(herdr-app ls 2>/dev/null); then
        echo "sessions: Herdr.app is not open, so neither session is in its window; reach them with hc attach okf-router-session and hc attach okf-worker-session"
        exit 0
    fi
    field() { python3 -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
    space=$(python3 -c 'import json, sys; print(next((s["id"] for s in json.load(sys.stdin)["spaces"] if s["name"] == sys.argv[1]), ""))' okf-builder <<<"$listed")
    placeholder=""
    if [ -z "$space" ]; then
        created=$(herdr-app do space.new --name okf-builder --folder "{{justfile_directory()}}" --tab placeholder --focus false)
        space=$(field space <<<"$created")
        placeholder=$(field tab <<<"$created")
    fi
    tab_of() { herdr-app ls | python3 -c 'import json, sys; print(next((t["id"] for s in json.load(sys.stdin)["spaces"] if s["id"] == sys.argv[1] for t in s["tabs"] if any(x["terminal"] == sys.argv[2] for x in t["terminals"])), ""))' "$space" "$1"; }
    placed=()
    place() {
        hc label "$1" herdr.space="$space" >/dev/null
        address=$(hc get --json "$1" | field address)
        tab=""
        for _ in $(seq 20); do
            tab=$(tab_of "$address")
            [ -n "$tab" ] && break
            sleep 0.25
        done
        if [ -z "$tab" ]; then
            echo "sessions: $1 is not in the Herdr.app space okf-builder; reach it with hc attach $1" >&2
            return 0
        fi
        herdr-app do tab.rename --id "$tab" --name "$2" >/dev/null
        placed+=("$1 is in the Herdr.app space okf-builder, in the tab $2")
    }
    place okf-router-session router
    place okf-worker-session worker
    if [ -n "$placeholder" ]; then
        herdr-app do tab.close --id "$placeholder" --confirmed true >/dev/null
    fi
    if [ "${#placed[@]}" -eq 2 ]; then
        echo "sessions: both are in the Herdr.app space okf-builder, in the tabs router and worker"
    elif [ "${#placed[@]}" -eq 1 ]; then
        echo "sessions: ${placed[0]}"
    fi

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
