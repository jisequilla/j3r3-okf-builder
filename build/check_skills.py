#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""check_skills.py — Check the frontmatter of every SKILL.md under a skills directory (Agent Skills standard).

Usage:
    uv run build/check_skills.py [plugin/okf-builder/skills]

For each <dir>/SKILL.md:
- the frontmatter parses as YAML and holds `name` and `description`;
- `name` equals the directory name, is lowercase letters, digits and hyphens, at most 64 characters;
- `description` is at most 1024 characters, and name and description together at most 1536;
- `description` is written in the third person: no "I", "me", "my", "you", "your", "we", "our" outside quoted
  trigger phrases ("what do we know about…" is the user's words, not the skill's).

Prints one line per problem and exits 1 if there is any; else prints the count of skills checked and exits 0.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
QUOTED_RE = re.compile(r'"[^"]*"|“[^”]*”')
PERSON_RE = re.compile(r"\b(I|me|my|you|your|yours|we|our|ours)\b", re.IGNORECASE)
LIMITS = {"name": 64, "description": 1024, "combined": 1536}


def problems(skill_md: Path) -> list[str]:
    where = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        return [f"{where}: SKILL.md has no frontmatter"]
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return [f"{where}: frontmatter is not YAML ({e.__class__.__name__})"]
    if not isinstance(fm, dict):
        return [f"{where}: frontmatter is not a mapping"]
    out = []
    name, desc = fm.get("name"), fm.get("description")
    if not isinstance(name, str) or not name:
        out.append(f"{where}: no name")
    else:
        if name != where:
            out.append(f"{where}: name '{name}' is not the directory name")
        if not NAME_RE.match(name) or len(name) > LIMITS["name"]:
            out.append(f"{where}: name '{name}' is not lowercase-hyphenated within {LIMITS['name']} characters")
    if not isinstance(desc, str) or not desc.strip():
        out.append(f"{where}: no description")
        return out
    if len(desc) > LIMITS["description"]:
        out.append(f"{where}: description has {len(desc)} characters > {LIMITS['description']}")
    if isinstance(name, str) and len(name) + len(desc) > LIMITS["combined"]:
        out.append(f"{where}: name and description have {len(name) + len(desc)} characters > {LIMITS['combined']}")
    person = sorted({m.group(1).lower() for m in PERSON_RE.finditer(QUOTED_RE.sub("", desc))})
    if person:
        out.append(f"{where}: description is not in the third person ({', '.join(person)})")
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0] if args else "plugin/okf-builder/skills")
    skills = sorted(root.glob("*/SKILL.md"))
    if not skills:
        print(f"check_skills: no */SKILL.md under {root}")
        return 1
    found = [p for s in skills for p in problems(s)]
    for p in found:
        print(p)
    if found:
        return 1
    print(f"{len(skills)} skills: frontmatter valid, descriptions within limits and in the third person")
    return 0


if __name__ == "__main__":
    sys.exit(main())
