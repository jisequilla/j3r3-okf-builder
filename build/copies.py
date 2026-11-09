#!/usr/bin/env python3
"""copies.py — Write the root copies of the standard and the templates from the plugin (ADR-0028 decision 2).

Usage:
    python3 build/copies.py [OUT]

Replaces OUT/standard/ with OKF-STANDARD.md and OKF-COMPATIBILITY.md from the okf-standard skill's references/,
and OUT/templates/ with its templates/*.md. OUT defaults to the repository root. Edit the source, never the copies.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "plugin" / "okf-builder" / "skills" / "okf-standard"
STANDARD = ("OKF-STANDARD.md", "OKF-COMPATIBILITY.md")


def write_copies(out: Path) -> None:
    for sub in ("standard", "templates"):
        shutil.rmtree(out / sub, ignore_errors=True)
        (out / sub).mkdir(parents=True)
    for name in STANDARD:
        shutil.copy2(REF / "references" / name, out / "standard" / name)
    for template in sorted((REF / "templates").glob("*.md")):
        shutil.copy2(template, out / "templates" / template.name)


if __name__ == "__main__":
    write_copies(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT)
