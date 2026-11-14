#!/usr/bin/env python3
"""check_marketplace_version.py — A change to the marketplace manifest raises its own version (DEC-0005).

Usage:
    python3 build/check_marketplace_version.py [BASE]    BASE defaults to origin/main

Compares .claude-plugin/marketplace.json with its copy at BASE. When the file differs, its top-level `version`
must be a higher semver than BASE's; when it does not differ, there is nothing to check. Exits 1 on a change
without a raised version, 0 otherwise. The plugin's own version lives in plugin.json and release-please raises it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ".claude-plugin/marketplace.json"


def semver(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def main(base: str) -> int:
    old = subprocess.run(["git", "show", f"{base}:{MANIFEST}"], cwd=ROOT, capture_output=True, text=True)
    if old.returncode != 0:
        print(f"{MANIFEST}: not at {base}, nothing to compare")
        return 0
    new_text = (ROOT / MANIFEST).read_text(encoding="utf-8")
    if json.loads(old.stdout) == json.loads(new_text):
        print(f"{MANIFEST}: unchanged since {base}")
        return 0
    before, after = json.loads(old.stdout).get("version"), json.loads(new_text).get("version")
    if not after or (before and semver(after) <= semver(before)):
        print(f"{MANIFEST} changed since {base} but its version did not rise ({before} → {after}): raise it")
        return 1
    print(f"{MANIFEST}: changed, version {before} → {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "origin/main"))
