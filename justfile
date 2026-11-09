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
