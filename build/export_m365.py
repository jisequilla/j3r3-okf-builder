#!/usr/bin/env python3
"""export_m365.py — Package the OKF skills for Microsoft 365 Copilot.

Builds two outputs from plugin/okf-builder/:

  dist/m365/okf-builder-m365.zip          M365 Copilot Cowork plugin (manifest.json v1.28
                                          + skills/ + icons). Upload it in M365 admin center >
                                          Manage apps > Upload custom app, or with
                                          `atk install --file-path ... --scope Personal`.
  dist/m365/skills/okf-<skill>.zip        One zip per skill (SKILL.md at the root) for
                                          "Upload a skill" in Copilot Studio / Agent Builder.
  dist/m365/okf-knowledge-architect-m365.zip
                                          The knowledge-architect declarative agent (v1.9),
                                          generated from plugin/okf-builder/agents/, with its own
                                          copy of the skills build/m365-agent.json lists
                                          (agent_skills must point inside the same app package).

Differences from the Claude plugin that this exporter resolves:
  - ${CLAUDE_PLUGIN_ROOT} does not exist: each skill must be self-contained. The scripts and
    templates a skill uses are copied into it, and paths are rewritten relative to the skill. The
    built-in Domain Profile (okf-standard/profiles/knowledge-3.0.md) is inlined into each copied
    okf_profile.py as BUILTIN_TEXT, so it adds no companion file.
  - M365 limit: ≤20 companion files per skill, ≤5 MB per file, no hidden files.
  - SKILL.md name == folder name (rule ASKILL-P006).
  - Declarative agent limits: instructions ≤ 8,000 characters, ≤ 8 agent_skills, name ≤ 100,
    description ≤ 1,000, one declarative agent per app. The Claude agent lists every skill it
    uses; build/m365-agent.json picks the M365 subset and the conversation starters (ADR-0017).

Usage:
    python3 build/export_m365.py [--out dist/m365] [--developer "Name"] [--website URL]
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
TEMPLATES = PLUGIN / "skills" / "okf-standard" / "templates"
# The concept templates: every template except the fragment, the conflict log and the ones only okf-init writes
CONCEPT_TEMPLATES = sorted(p.name for p in TEMPLATES.glob("*.md")
                           if p.name not in ("fragment.md", "conflict-log.md", "root-index.md", "log.md", "project.md"))
WRITE_SCRIPTS = ["okf_index.py", "okf_lint.py", "okf_profile.py", "okf_migrate.py", "okf_common.py"]
NEEDS = {
    "okf-standard": {"scripts": [], "templates": False},
    "okf-init":     {"scripts": ["okf_init.py", "okf_common.py", "okf_index.py", "okf_migrate.py", "okf_lint.py", "okf_profile.py", "okf_obsidian.py"], "templates": ["project.md", "log.md"]},
    "okf-capture":  {"scripts": WRITE_SCRIPTS, "templates": CONCEPT_TEMPLATES},
    "okf-fragment": {"scripts": WRITE_SCRIPTS, "templates": ["fragment.md"]},
    "okf-distill":  {"scripts": WRITE_SCRIPTS, "templates": CONCEPT_TEMPLATES + ["conflict-log.md"]},
    "okf-review":   {"scripts": ["okf_index.py", "okf_lint.py", "okf_profile.py", "okf_audit.py", "okf_common.py"], "templates": False},
    "okf-lint":     {"scripts": ["okf_lint.py", "okf_profile.py", "okf_common.py"], "templates": False},
    "okf-index":    {"scripts": ["okf_index.py", "okf_common.py", "okf_lint.py", "okf_profile.py"], "templates": False},
    "okf-migrate":  {"scripts": ["okf_migrate.py", "okf_common.py", "okf_lint.py", "okf_profile.py", "okf_index.py"], "templates": False},
    "okf-ask":      {"scripts": ["okf_lint.py", "okf_profile.py", "okf_common.py"], "templates": False},
    "okf-projection": {"scripts": ["okf_projection.py", "okf_lint.py", "okf_profile.py", "okf_common.py"], "templates": False},
}
# A script only one skill ships: another skill that names it points to that skill's copy, so the script adds no
# companion file to it (okf-distill already carries the 20 the limit allows)
SCRIPT_HOMES = {"okf_projection.py": "okf-projection"}
# A template only one skill ships, for the same reason: another skill that names it points to that skill's copy
TEMPLATE_HOMES = {"decision.md": "okf-capture"}
MAX_COMPANIONS = 20
# The built-in Domain Profile goes inside each exported okf_profile.py, so it adds no companion file
BUILTIN_PROFILE = PLUGIN / "skills" / "okf-standard" / "profiles" / "knowledge-3.0.md"
BUILTIN_LINE = "BUILTIN_TEXT: str | None = None\n"


def inline_builtin(script: Path) -> None:
    """Replace okf_profile.py's empty BUILTIN_TEXT with the built-in profile's text, as a Python literal."""
    text = script.read_text(encoding="utf-8")
    if text.count(BUILTIN_LINE) != 1:
        raise SystemExit(f"{script}: expected one line {BUILTIN_LINE.strip()!r} to inline the built-in profile into")
    literal = repr(BUILTIN_PROFILE.read_text(encoding="utf-8"))
    script.write_text(text.replace(BUILTIN_LINE, f"BUILTIN_TEXT: str | None = {literal}\n"), encoding="utf-8")


# The paths note of the source SKILL.md files ("Rutas" until the skill prose is translated)
PATHS_NOTE_RE = re.compile(r"^> \*\*(?:Rutas|Paths)\.\*\*.*$\n?", re.M)


# The source okf-standard's inventory of where scripts, templates and references live
INVENTORY_RE = re.compile(r"^## Where everything is .*?^```\n.*?^```\n", re.M | re.S)
M365_INVENTORY = """## Where everything is

In this package each skill carries the scripts and templates it uses, in its own `scripts/` and `templates/`. This skill carries only the references:

```
references/OKF-STANDARD.md | OKF-COMPATIBILITY.md | OKF-SPEC-v0.1.md | OKF-SPEC-v0.2.md
```
"""


# okf-distill's Closing mode runs okf_close.py, which no M365 skill ships (SDR-0024 decision 12): the section becomes a
# note, and the routing sentence and the description's closing sentence go
CLOSING_RE = re.compile(r"^## Closing mode\n.*?(?=^## |\Z)", re.M | re.S)
M365_NO_CLOSING = ("## Closing mode\n\nClosing an operational instance is not available in Microsoft 365 Copilot: it needs "
                   "okf_close.py, which this package does not ship. Close the instance from Claude Code or from the GitHub "
                   "Copilot pack.\n")
CLOSING_ROUTING = ("To close an operational instance into its parent, follow **Closing mode**, at the end of this skill, "
                   "instead of these steps.\n\n")
CLOSING_DESCRIPTION = (' Also closes an operational instance into its parent through okf_close.py ("close this request", '
                       '"close the instance", "okf close").')


def strip_closing(text: str) -> str:
    """okf-distill's SKILL.md without its Closing mode, its routing sentence and its description's closing sentence."""
    if "okf_close" not in text:
        return text
    for part in (CLOSING_ROUTING, CLOSING_DESCRIPTION):
        if text.count(part) != 1:
            raise SystemExit(f"okf-distill: SKILL.md does not hold this text once, so its closing cannot be removed: {part!r}")
    text = text.replace(CLOSING_ROUTING, "").replace(CLOSING_DESCRIPTION, "")
    text, n = CLOSING_RE.subn(M365_NO_CLOSING, text)
    if n != 1 or "okf_close" in CLOSING_RE.sub("", text):
        raise SystemExit("okf-distill: SKILL.md names okf_close outside its one ## Closing mode section")
    return text


def templates_of(skill: str) -> list[str]:
    """The templates the skill's M365 copy carries: those it needs, less the ones another skill is the home of."""
    return [name for name in NEEDS[skill]["templates"] or [] if TEMPLATE_HOMES.get(name, skill) == skill]


def ships(skill: str) -> list[str]:
    """What the skill's M365 copy carries besides SKILL.md, as prose fragments."""
    parts = []
    if NEEDS[skill]["scripts"]:
        parts.append("scripts in `scripts/`")
    if templates_of(skill):
        parts.append("templates in `templates/`")
    return parts


def rewrite(text: str, skill: str) -> str:
    parts = ships(skill)
    text = PATHS_NOTE_RE.sub(f"> **Paths.** This skill is self-contained: {' and '.join(parts)} of its own base directory.\n"
                             if parts else "", text)
    if skill == "okf-distill":
        text = strip_closing(text)
    if skill == "okf-standard":
        text = INVENTORY_RE.sub(M365_INVENTORY, text)
        text = text.replace("<skills>/okf-standard/references/", "references/")
    for script, home in SCRIPT_HOMES.items():
        if skill != home and script not in NEEDS[skill]["scripts"]:
            text = text.replace(f"<skills>/okf-standard/scripts/{script}", f"({home} skill) scripts/{script}")
    # Each M365 skill is self-contained: <skills>/okf-standard/scripts → the skill's own scripts/
    text = text.replace("<skills>/okf-standard/scripts/", "scripts/")
    for template, home in TEMPLATE_HOMES.items():
        if template not in templates_of(skill):
            text = text.replace(f"<skills>/okf-standard/templates/{template}", f"({home} skill) templates/{template}")
    if templates_of(skill):
        text = text.replace("<skills>/okf-standard/templates/", "templates/")
    else:
        text = text.replace("<skills>/okf-standard/templates/", "(template carried by the skill that writes that type) templates/")
    text = text.replace("<skills>/okf-standard/references/", "(okf-standard skill) references/")
    text = text.replace("`<skills>/okf-standard/profiles/knowledge-3.0.md`",
                        "`profiles/knowledge-3.0.md` (inlined in the `okf_profile.py` of each skill that ships it)")
    text = text.replace("<skills>/", "(skill) ")
    text = text.replace("${CLAUDE_PLUGIN_ROOT}/skills", "(skills)")
    return text


def m365_note(skill: str) -> str:
    """Environment note appended to each M365 skill, matching what that skill ships."""
    if NEEDS[skill]["scripts"]:
        run = ("The `scripts/*.py` scripts run\nfrom the base directory of this skill with `uv run`, which installs PyYAML, and take the bundle\n"
               "path as an argument; without uv, `python3` works if PyYAML is installed. If the environment\n"
               "cannot run scripts, apply the same rules by hand from the standard and the\ntemplates, and say so explicitly.")
    else:
        run = ("This skill ships no scripts: the skills that write or check a bundle carry their own.\n"
               "If they cannot run in this environment, apply the rules by hand from the standard and say so explicitly.")
    return ("\n\n## Environment note (Microsoft 365 Copilot)\n\n"
            "This skill runs in Microsoft 365 Copilot, not in a terminal on the repository. The `knowledge/`\n"
            "bundle arrives as a SharePoint folder synced with OneDrive, read-only through the GitHub connector, or as attached files.\n"
            f"Ask the user for the path or the folder if it is not obvious. {run}\n")


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
    # 20-companion limit: scripts and templates go into the skills that use them, the built-in profile into okf_profile.py
    if skill == "okf-standard":
        for sub in ("scripts", "templates", "profiles"):
            if (dst / sub).exists():
                shutil.rmtree(dst / sub)
    need = NEEDS[skill]
    if "okf_lint.py" in need["scripts"] and "okf_profile.py" not in need["scripts"]:
        raise SystemExit(f"{skill}: ships okf_lint.py without okf_profile.py, which it imports")
    if need["scripts"]:
        (dst / "scripts").mkdir(exist_ok=True)
        for s in need["scripts"]:
            shutil.copy2(SCRIPTS / s, dst / "scripts" / s)
            if s == "okf_profile.py":
                inline_builtin(dst / "scripts" / s)
    if templates_of(skill):
        (dst / "templates").mkdir(exist_ok=True)
        for name in templates_of(skill):
            shutil.copy2(TEMPLATES / name, dst / "templates" / name)
    for md in dst.rglob("*.md"):
        md.write_text(rewrite(md.read_text(encoding="utf-8"), skill), encoding="utf-8")
    sk = dst / "SKILL.md"
    sk.write_text(ensure_frontmatter(sk.read_text(encoding="utf-8"), skill, author).rstrip() + m365_note(skill), encoding="utf-8")
    companions = [p for p in dst.rglob("*") if p.is_file() and p.name != "SKILL.md"]
    if len(companions) > MAX_COMPANIONS:
        raise SystemExit(f"{skill}: {len(companions)} companion files > {MAX_COMPANIONS}")
    for p in companions:
        if p.stat().st_size > 5 * 1024 * 1024 or p.name.startswith("."):
            raise SystemExit(f"{skill}: file not valid for M365: {p}")
    missing = unshipped_paths(dst)
    if missing:
        raise SystemExit(f"{skill}: SKILL.md names files its M365 copy does not ship: {', '.join(missing)}")
    return len(companions)


# A path the skill points to in its own folder; a "(... skill)" or "(template carried ...)" prefix means another skill holds it
OWN_PATH_RE = re.compile(r"(?<![\w/])((?:scripts|templates|references)/[A-Za-z0-9_.-]+\.(?:py|md))")


def unshipped_paths(dst: Path) -> list[str]:
    """Paths named in the M365 SKILL.md as the skill's own that are not in its folder."""
    text = (dst / "SKILL.md").read_text(encoding="utf-8")
    named = set()
    for m in OWN_PATH_RE.finditer(text):
        before = text[max(0, m.start() - 2):m.start()]
        if before.endswith(") "):
            continue
        named.add(m.group(1))
    return sorted(n for n in named if not (dst / n).exists())


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


AGENT_SRC = PLUGIN / "agents" / "knowledge-architect.md"
AGENT_CONFIG = ROOT / "build" / "m365-agent.json"
AGENT_LIMITS = {"instructions": 8000, "skills": 8, "name": 100, "description": 1000}


def read_agent(path: Path, config_path: Path = AGENT_CONFIG) -> dict:
    """Read the Claude agent source and the M365 config (ADR-0017): name, description, body and the M365 skill subset."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(encoding="utf-8"), re.S)
    if not m:
        raise SystemExit(f"{path}: no frontmatter")
    fm, body = m.group(1), m.group(2).strip()
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    block = re.search(r"^skills:\s*\n((?:\s+-\s*.+\n?)+)", fm, re.M)
    if not (name and desc and block):
        raise SystemExit(f"{path}: needs name, description and a skills list")
    claude_skills = [ln.split("-", 1)[1].strip() for ln in block.group(1).splitlines() if ln.strip()]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    skills = config.get("agent_skills") or []
    starters = config.get("conversation_starters") or []
    agent = {"name": name.group(1).strip(), "description": desc.group(1).strip(), "claude_skills": claude_skills,
             "skills": skills, "starters": starters, "instructions": body}
    problems = []
    if len(body) > AGENT_LIMITS["instructions"]:
        problems.append(f"body has {len(body)} characters > {AGENT_LIMITS['instructions']}")
    if not skills:
        problems.append(f"{config_path.name}: agent_skills is empty")
    if len(skills) > AGENT_LIMITS["skills"]:
        problems.append(f"{config_path.name}: {len(skills)} agent_skills > {AGENT_LIMITS['skills']}")
    if len(set(skills)) != len(skills):
        problems.append(f"{config_path.name}: agent_skills has duplicates")
    if len(agent["description"]) > AGENT_LIMITS["description"]:
        problems.append(f"description has {len(agent['description'])} characters > {AGENT_LIMITS['description']}")
    missing = [sk for sk in claude_skills + skills if not (PLUGIN / "skills" / sk / "SKILL.md").exists()]
    if missing:
        problems.append(f"skills not in the plugin: {', '.join(sorted(set(missing)))}")
    outside = [sk for sk in skills if sk not in claude_skills]
    if outside:
        problems.append(f"{config_path.name}: agent_skills not in the Claude agent's skills: {', '.join(outside)}")
    if problems:
        raise SystemExit(f"{path.name}: " + "; ".join(problems))
    return agent


def build_agent_package(out: Path, built_skills: Path, base_manifest: dict) -> Path:
    """Declarative agent package: manifest + declarativeAgent.json + its own copy of the skills it lists."""
    agent = read_agent(AGENT_SRC)
    apkg = out / "agent-package"
    (apkg / "skills").mkdir(parents=True)
    for sk in agent["skills"]:
        shutil.copytree(built_skills / sk, apkg / "skills" / sk)
    for icon in ("color.png", "outline.png"):
        if (built_skills.parent / icon).exists():
            shutil.copy2(built_skills.parent / icon, apkg / icon)
    declarative = {
        "$schema": "https://developer.microsoft.com/json-schemas/copilot/declarative-agent/v1.9/schema.json",
        "version": "v1.9",
        "name": "OKF Knowledge Architect",
        "description": agent["description"],
        "instructions": agent["instructions"],
        "agent_skills": [{"folder": f"./skills/{sk}"} for sk in agent["skills"]],
        "conversation_starters": agent["starters"],
    }
    (apkg / "declarativeAgent.json").write_text(json.dumps(declarative, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = dict(base_manifest)
    manifest.pop("agentSkills", None)
    manifest["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, base_manifest["developer"]["websiteUrl"] + "#okf-knowledge-architect"))
    manifest["name"] = {"short": "OKF Knowledge Architect", "full": "OKF Knowledge Architect — distills and curates a project's knowledge"}
    manifest["description"] = {"short": "Agent that curates knowledge/ in OKF format with a person approving each change",
                               "full": agent["description"]}
    manifest["copilotAgents"] = {"declarativeAgents": [{"id": "knowledgeArchitect", "file": "declarativeAgent.json"}]}
    (apkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zp = out / "okf-knowledge-architect-m365.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(apkg.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(apkg))
    print(f"agent {agent['name']}: {len(agent['instructions'])} instruction characters, "
          f"{len(agent['skills'])} M365 skills of {len(agent['claude_skills'])} in Claude")
    return zp


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
    azp = build_agent_package(out, pkg / "skills", manifest)
    (out / "README.md").write_text(f"""# OKF for Microsoft 365 Copilot

## A) M365 Copilot Cowork plugin — `okf-builder-m365.zip`
M365 package (manifest v1.28 + {len(skills)} Agent Skills). Requires Microsoft 365 Copilot and, for now, the Frontier program for Cowork.
- Tenant (admin): M365 admin center → Manage apps → Upload custom app → Add agent → upload the zip. It shows up in Cowork → Sources & Skills → Plugins.
- Personal (no admin): `npm i -g @microsoft/m365agentstoolkit-cli && atk auth login && atk install --file-path okf-builder-m365.zip --scope Personal`.
- Optional validation: `wiqd plugin validate` (Microsoft preview CLI).

## B) Standalone skills — `skills/okf-*.zip`
For Copilot Studio (new agent experience) or Agent Builder: Build → Skills → Upload a skill → drag each zip. Upload at least `okf-standard`, `okf-ask` and `okf-capture`.

## C) Knowledge-architect agent — `okf-knowledge-architect-m365.zip`
A declarative agent (schema v1.9) generated from `plugin/okf-builder/agents/knowledge-architect.md`: its body becomes
the instructions and its skills list becomes `agent_skills`, each skill copied into this package. Install it the same
way as A). It is a separate package so that it cannot break A): whether one package can carry both app-level skills and
a declarative agent has not been tested in a tenant.

## Knowledge
A bundle has one source, a Git repository or a SharePoint document library, and M365 Copilot reads it there:
- Git source: connect the repository with the GitHub Cloud Knowledge connector, which indexes `.md` files and keeps
  GitHub permissions. It needs a Copilot licence or metered use and a GitHub-to-Entra identity mapping. M365 only reads;
  changes go back to the repository by PR.
- SharePoint source, for teams without Git: the `knowledge/` folder lives in the library and is edited through the
  OneDrive sync client; add the library as a knowledge source of the agent. Microsoft does not document `.md` as a
  SharePoint knowledge file type, so check in the tenant that Copilot answers from those files before relying on it.

Generated with `build/export_m365.py`; do not edit here.
""", encoding="utf-8")
    print(f"→ {zp}\n→ {azp}\n→ {out / 'skills'}/*.zip\n{len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
