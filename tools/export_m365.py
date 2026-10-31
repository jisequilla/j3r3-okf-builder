#!/usr/bin/env python3
"""export_m365.py — Package the OKF skills for Microsoft 365 Copilot.

Builds two outputs from plugin/okf-builder/:

  dist/m365/okf-builder-m365.zip          M365 Copilot Cowork plugin (manifest.json v1.28
                                          + skills/ + icons). Upload it in M365 admin center >
                                          Manage apps > Upload custom app, or with
                                          `atk install --file-path ... --scope Personal`.
  dist/m365/skills/okf-<skill>.zip        One zip per skill (SKILL.md at the root) for
                                          "Upload a skill" in Copilot Studio / Agent Builder.

Differences from the Claude plugin that this exporter resolves:
  - ${CLAUDE_PLUGIN_ROOT} does not exist: each skill must be self-contained. The scripts and
    templates a skill uses are copied into it, and paths are rewritten relative to the skill.
  - M365 limit: ≤20 companion files per skill, ≤5 MB per file, no hidden files.
  - SKILL.md name == folder name (rule ASKILL-P006).

Usage:
    python3 tools/export_m365.py [--out dist/m365] [--developer "Name"] [--website URL]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "okf-builder"
SCRIPTS = PLUGIN / "skills" / "okf-standard" / "scripts"
PLUGIN_JSON = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

# Which scripts/templates each skill needs (to be self-contained)
NEEDS = {
    "okf-standard": {"scripts": [], "templates": True},
    "okf-init":     {"scripts": ["okf_init.py", "okf_common.py", "okf_index.py", "okf_migrate.py"], "templates": True},
    "okf-capture":  {"scripts": ["okf_index.py", "okf_lint.py", "okf_migrate.py", "okf_common.py"], "templates": True},
    "okf-lint":     {"scripts": ["okf_lint.py", "okf_common.py"], "templates": False},
    "okf-index":    {"scripts": ["okf_index.py", "okf_common.py"], "templates": False},
    "okf-migrate":  {"scripts": ["okf_migrate.py", "okf_common.py", "okf_lint.py"], "templates": False},
    "okf-ask":      {"scripts": ["okf_lint.py", "okf_common.py"], "templates": False},
}
MAX_COMPANIONS = 20


# The paths note of the source SKILL.md files ("Rutas" until the skill prose is translated)
PATHS_NOTE_RE = re.compile(r"^> \*\*(?:Rutas|Paths)\.\*\*.*$\n?", re.M)


def rewrite(text: str, skill: str) -> str:
    text = PATHS_NOTE_RE.sub("> **Paths.** This skill is self-contained: scripts in `scripts/` and templates in `templates/` of its own base directory.\n"
                        if NEEDS[skill]["templates"] or NEEDS[skill]["scripts"] else "", text)
    # Each M365 skill is self-contained: <skills>/okf-standard/scripts → the skill's own scripts/
    text = text.replace("<skills>/okf-standard/scripts/", "scripts/")
    if NEEDS[skill]["templates"]:
        text = text.replace("<skills>/okf-standard/templates/", "templates/")
    else:
        text = text.replace("<skills>/okf-standard/templates/", "(templates: okf-standard skill) templates/")
    text = text.replace("<skills>/okf-standard/references/", "(okf-standard skill) references/")
    text = text.replace("<skills>/", "(skill) ")
    text = text.replace("${CLAUDE_PLUGIN_ROOT}/skills", "(skills)")
    return text


M365_NOTE = """

## Environment note (Microsoft 365 Copilot)

This skill runs in Microsoft 365 Copilot, not in a terminal on the repository. The `knowledge/`
bundle arrives as a SharePoint folder synced with OneDrive, read-only through the GitHub connector, or as attached files.
Ask the user for the path or the folder if it is not obvious. The `scripts/*.py` scripts run
from the base directory of this skill with `uv run`, which installs PyYAML, and take the bundle
path as an argument; without uv, `python3` works if PyYAML is installed. If the environment
cannot run scripts, apply the same rules by hand from `references/` and the
templates, and say so explicitly.
"""


def ensure_frontmatter(text: str, skill: str, author: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit(f"{skill}: SKILL.md has no frontmatter")
    fm = m.group(1)
    if not re.search(rf"^name:\s*{re.escape(skill)}\s*$", fm, re.M):
        fm = re.sub(r"^name:.*$", f"name: {skill}", fm, flags=re.M)
    if "license:" not in fm:
        fm += "\nlicense: Apache-2.0"
    if "metadata:" not in fm:
        fm += f'\nmetadata:\n  author: {author}\n  version: "{PLUGIN_JSON["version"]}"'
    return f"---\n{fm}\n---\n" + text[m.end():]


def build_skill(skill_src: Path, dst: Path, author: str) -> int:
    skill = skill_src.name
    shutil.copytree(skill_src, dst, ignore=shutil.ignore_patterns("__pycache__", ".*"))
    if skill == "okf-standard" and (dst / "scripts").exists():
        shutil.rmtree(dst / "scripts")  # 20-companion limit; the scripts go into the skills that use them
    need = NEEDS[skill]
    if need["scripts"]:
        (dst / "scripts").mkdir(exist_ok=True)
        for s in need["scripts"]:
            shutil.copy2(SCRIPTS / s, dst / "scripts" / s)
    if need["templates"] and skill != "okf-standard":
        shutil.copytree(PLUGIN / "skills" / "okf-standard" / "templates", dst / "templates")
    for md in dst.rglob("*.md"):
        md.write_text(rewrite(md.read_text(encoding="utf-8"), skill), encoding="utf-8")
    sk = dst / "SKILL.md"
    sk.write_text(ensure_frontmatter(sk.read_text(encoding="utf-8"), skill, author).rstrip() + M365_NOTE, encoding="utf-8")
    companions = [p for p in dst.rglob("*") if p.is_file() and p.name != "SKILL.md"]
    if len(companions) > MAX_COMPANIONS:
        raise SystemExit(f"{skill}: {len(companions)} companion files > {MAX_COMPANIONS}")
    for p in companions:
        if p.stat().st_size > 5 * 1024 * 1024 or p.name.startswith("."):
            raise SystemExit(f"{skill}: file not valid for M365: {p}")
    return len(companions)


def make_icons(out: Path) -> None:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:  # noqa: BLE001
        src = PLUGIN / ".claude-plugin" / "icon.png"
        shutil.copy2(src, out / "color.png")
        shutil.copy2(src, out / "outline.png")
        print("warning: PIL not available; icons not resized (192x192 / 32x32 required)")
        return
    img = Image.open(PLUGIN / ".claude-plugin" / "icon.png").convert("RGBA")
    img.resize((192, 192)).save(out / "color.png")
    o = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    for i in range(3):
        d.rounded_rectangle([5 + i * 3, 5 + i * 3, 22 + i * 3, 22 + i * 3], radius=3, outline=(255, 255, 255, 255), width=2)
    o.save(out / "outline.png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist/m365", help="output directory (relative to the repo)")
    ap.add_argument("--developer", default=PLUGIN_JSON.get("author", {}).get("name", "okf-builder"), help="developer name for the manifest")
    ap.add_argument("--website", default="https://github.com/jisequilla/j3r3-okf-builder", help="developer website for the manifest")
    args = ap.parse_args(argv)

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    pkg = out / "package"
    (pkg / "skills").mkdir(parents=True)
    (out / "skills").mkdir()

    skills = []
    for skill_src in sorted((PLUGIN / "skills").iterdir()):
        if not (skill_src / "SKILL.md").exists():
            continue
        n = build_skill(skill_src, pkg / "skills" / skill_src.name, args.developer)
        skills.append(skill_src.name)
        print(f"skill {skill_src.name}: {n} companions")
        # one zip per skill for Copilot Studio / Agent Builder (SKILL.md at the zip root)
        zp = out / "skills" / f"{skill_src.name}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted((pkg / "skills" / skill_src.name).rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(pkg / "skills" / skill_src.name))

    make_icons(pkg)
    manifest = {
        "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.28/MicrosoftTeams.schema.json",
        "manifestVersion": "1.28",
        "version": PLUGIN_JSON["version"],
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, args.website + "#okf-builder")),
        "developer": {
            "name": args.developer,
            "websiteUrl": args.website,
            "privacyUrl": args.website + "#privacy",
            "termsOfUseUrl": args.website + "#terms",
        },
        "name": {"short": "OKF Builder", "full": "OKF Builder — project knowledge in Open Knowledge Format"},
        "description": {
            "short": "Manage knowledge/ in OKF format: scaffold, capture, validation, queries",
            "full": PLUGIN_JSON["description"],
        },
        "icons": {"color": "color.png", "outline": "outline.png"},
        "accentColor": "#1F2A44",
        "agentSkills": [{"folder": f"./skills/{s}"} for s in skills],
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    zp = out / "okf-builder-m365.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pkg.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pkg))
    (out / "README.md").write_text(f"""# OKF for Microsoft 365 Copilot

## A) M365 Copilot Cowork plugin — `okf-builder-m365.zip`
M365 package (manifest v1.28 + {len(skills)} Agent Skills). Requires Microsoft 365 Copilot and, for now, the Frontier program for Cowork.
- Tenant (admin): M365 admin center → Manage apps → Upload custom app → Add agent → upload the zip. It shows up in Cowork → Sources & Skills → Plugins.
- Personal (no admin): `npm i -g @microsoft/m365agentstoolkit-cli && atk auth login && atk install --file-path okf-builder-m365.zip --scope Personal`.
- Optional validation: `wiqd plugin validate` (Microsoft preview CLI).

## B) Standalone skills — `skills/okf-*.zip`
For Copilot Studio (new agent experience) or Agent Builder: Build → Skills → Upload a skill → drag each zip. Upload at least `okf-standard`, `okf-ask` and `okf-capture`.

## Knowledge
A bundle has one source, a Git repository or a SharePoint document library, and M365 Copilot reads it there:
- Git source: connect the repository with the GitHub Cloud Knowledge connector, which indexes `.md` files and keeps
  GitHub permissions. It needs a Copilot licence or metered use and a GitHub-to-Entra identity mapping. M365 only reads;
  changes go back to the repository by PR.
- SharePoint source, for teams without Git: the `knowledge/` folder lives in the library and is edited through the
  OneDrive sync client; add the library as a knowledge source of the agent. Microsoft does not document `.md` as a
  SharePoint knowledge file type, so check in the tenant that Copilot answers from those files before relying on it.

Generated with `tools/export_m365.py`; do not edit here.
""", encoding="utf-8")
    print(f"→ {zp}\n→ {out / 'skills'}/*.zip\n{len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
